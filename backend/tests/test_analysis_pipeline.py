"""End-to-end integration tests for AnalysisPipeline."""

import pytest
from pathlib import Path
from git import Repo

from app.core.config import settings
from app.models import APIChange, Commit, DocumentationVersion
from app.schemas.repository import RepositoryCreate
from app.services.pipeline.analysis_pipeline import AnalysisPipeline
from app.services.repository_service import RepositoryService


@pytest.mark.asyncio
async def test_end_to_end_analysis_pipeline_flow(db_session, tmp_path, monkeypatch):
    """Test full pipeline execution: Git commit -> Change detection -> AI reasoning -> OpenAPI update -> Validation -> Publication."""
    # 1. Initialize local Git repository
    repo_dir = tmp_path / "backend_repo"
    repo_dir.mkdir()
    git_repo = Repo.init(repo_dir)
    git_repo.config_writer().set_value("user", "name", "Author").release()
    git_repo.config_writer().set_value("user", "email", "author@example.com").release()

    # Commit 1: Initial FastAPI code
    (repo_dir / "app").mkdir()
    main_file = repo_dir / "app" / "main.py"
    main_file.write_text(
        """from fastapi import FastAPI
app = FastAPI()

@app.get('/users')
def list_users():
    return [{'id': 1, 'name': 'Alice'}]
""",
        encoding="utf-8",
    )
    git_repo.index.add(["app/main.py"])
    commit1 = git_repo.index.commit("Initial version with GET /users")

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage"))

    # Connect repository
    repo_in = RepositoryCreate(
        owner="test-org",
        name="backend-repo",
        clone_url=str(repo_dir),
        default_branch="master" if "master" in [h.name for h in git_repo.heads] else "main",
        confidence_threshold=0.85,
    )
    db_repo = await RepositoryService.connect_repository(db_session, repo_in)

    pipeline = AnalysisPipeline()

    # Process Commit 1
    res1 = await pipeline.process_commit_event(
        db=db_session,
        repository=db_repo,
        before_sha=None,
        after_sha=commit1.hexsha,
        commit_message="Initial version with GET /users",
    )
    assert res1["status"] in ("COMPLETED", "NO_CHANGES")

    # Verify baseline documentation version 1 exists
    doc_v1 = db_session.query(DocumentationVersion).filter(DocumentationVersion.repository_id == db_repo.id).first()
    assert doc_v1 is not None
    assert doc_v1.version == 1
    assert "/users" in doc_v1.openapi_json["paths"]
    assert "get" in doc_v1.openapi_json["paths"]["/users"]

    # Commit 2: Add POST /users and modify schema
    (repo_dir / "app" / "schemas").mkdir()
    schema_file = repo_dir / "app" / "schemas" / "user.py"
    schema_file.write_text(
        """from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    name: str = Field(..., description="Full Name")
    email: str = Field(..., description="Email Address")
""",
        encoding="utf-8",
    )

    main_file.write_text(
        """from fastapi import FastAPI
from app.schemas.user import UserCreate
app = FastAPI()

@app.get('/users')
def list_users():
    return [{'id': 1, 'name': 'Alice'}]

@app.post('/users', status_code=201)
def create_user(user: UserCreate):
    return user
""",
        encoding="utf-8",
    )

    git_repo.index.add(["app/schemas/user.py", "app/main.py"])
    commit2 = git_repo.index.commit("Add POST /users with UserCreate schema")

    # Process Commit 2
    res2 = await pipeline.process_commit_event(
        db=db_session,
        repository=db_repo,
        before_sha=commit1.hexsha,
        after_sha=commit2.hexsha,
        commit_message="Add POST /users with UserCreate schema",
    )

    assert res2["status"] == "COMPLETED"
    assert res2["api_changes_count"] >= 1
    assert res2["published"] is True

    # Verify Documentation Version 2 was published
    doc_versions = db_session.query(DocumentationVersion).filter(
        DocumentationVersion.repository_id == db_repo.id
    ).order_by(DocumentationVersion.version.desc()).all()

    assert len(doc_versions) >= 2
    latest_doc = doc_versions[0]
    assert latest_doc.version == 2
    assert "post" in latest_doc.openapi_json["paths"]["/users"]

    # Verify APIChange record was stored
    changes = db_session.query(APIChange).filter(APIChange.repository_id == db_repo.id).all()
    assert len(changes) >= 1
    post_change = next((c for c in changes if c.method == "POST"), None)
    assert post_change is not None
    assert post_change.confidence >= 0.85
    assert post_change.status == "AUTO_APPLIED"

    # 3. Test Idempotency: re-processing commit2 should skip
    res_duplicate = await pipeline.process_commit_event(
        db=db_session,
        repository=db_repo,
        before_sha=commit1.hexsha,
        after_sha=commit2.hexsha,
    )
    assert "idempotent skip" in res_duplicate["message"].lower()
