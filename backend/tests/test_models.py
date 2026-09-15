"""Tests for database models, relationships, and constraints."""

from datetime import datetime, timezone
from app.models import Repository, Commit, APIChange, DocumentationVersion, AgentRun


def test_repository_models_and_cascade(db_session):
    """Test full database model hierarchy, relationships, and cascading deletes."""
    # 1. Create Repository
    repo = Repository(
        owner="test-org",
        name="test-repo",
        default_branch="main",
        clone_url="https://github.com/test-org/test-repo.git",
        framework="fastapi",
        confidence_threshold=0.85,
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    assert repo.id is not None
    assert repo.full_name == "test-org/test-repo"

    # 2. Add Commit
    commit = Commit(
        repository_id=repo.id,
        commit_sha="a1b2c3d4e5f6",
        message="Add user routes",
        author="Dev <dev@example.com>",
        timestamp=datetime.now(timezone.utc),
        status="COMPLETED",
    )
    db_session.add(commit)
    db_session.commit()
    db_session.refresh(commit)

    assert commit.id is not None
    assert commit.repository.name == "test-repo"

    # 3. Add APIChange
    change = APIChange(
        repository_id=repo.id,
        commit_id=commit.id,
        change_type="added",
        method="POST",
        path="/users",
        summary="Create user endpoint",
        old_structure=None,
        new_structure={"request": {"name": "string"}},
        ai_explanation="Added POST /users endpoint for user registration",
        impact_analysis={"severity": "LOW", "reason": "New endpoint is additive and non-breaking"},
        confidence=0.98,
        status="AUTO_APPLIED",
        source_file="app/routes/users.py",
        source_line=15,
    )
    db_session.add(change)

    # 4. Add DocumentationVersion
    doc = DocumentationVersion(
        repository_id=repo.id,
        commit_id=commit.id,
        version=1,
        openapi_json={"openapi": "3.0.3", "info": {"title": "Test API", "version": "1.0.0"}, "paths": {}},
        validation_status="VALID",
    )
    db_session.add(doc)

    # 5. Add AgentRun
    agent_run = AgentRun(
        repository_id=repo.id,
        commit_id=commit.id,
        input_data={"diff": "some git diff"},
        output_data={"changes": []},
        model="gemini-2.5-flash",
        status="SUCCESS",
    )
    db_session.add(agent_run)
    db_session.commit()

    # Query back and verify relationships
    db_session.refresh(repo)
    assert len(repo.commits) == 1
    assert len(repo.api_changes) == 1
    assert len(repo.documentation_versions) == 1
    assert len(repo.agent_runs) == 1

    # Verify cascading delete
    db_session.delete(repo)
    db_session.commit()

    assert db_session.query(Repository).count() == 0
    assert db_session.query(Commit).count() == 0
    assert db_session.query(APIChange).count() == 0
    assert db_session.query(DocumentationVersion).count() == 0
    assert db_session.query(AgentRun).count() == 0
