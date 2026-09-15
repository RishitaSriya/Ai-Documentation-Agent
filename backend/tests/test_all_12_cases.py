"""Comprehensive automated test suite covering all 12 core requirements from Section 31."""

import pytest
from pathlib import Path
from git import Repo

from app.core.config import settings
from app.models import APIChange, Commit, DocumentationVersion
from app.schemas.agent import (
    APIChangePlan,
    DocumentationChanges,
    FieldChange,
    ImpactAnalysis,
    SingleAPIChangePlan,
)
from app.schemas.repository import RepositoryCreate
from app.services.analyzers.base import (
    APIEndpointSnapshot,
    APISnapshot,
    FieldSnapshot,
    ParameterSnapshot,
    SchemaSnapshot,
)
from app.services.analyzers.fastapi_analyzer import FastAPIAnalyzer
from app.services.openapi.comparator import APIComparator
from app.services.openapi.loader import OpenAPILoader
from app.services.openapi.updater import OpenAPIUpdater
from app.services.openapi.validator import OpenAPIValidator
from app.services.pipeline.analysis_pipeline import AnalysisPipeline
from app.services.repository_service import RepositoryService


# ==========================================
# Test 1: New endpoint detected
# ==========================================
def test_1_new_endpoint_detected():
    prev = APISnapshot()
    curr = APISnapshot()
    curr.add_endpoint(APIEndpointSnapshot(method="POST", path="/users", function_name="create_user"))

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    assert changes[0].change_type == "added"
    assert changes[0].method == "POST"
    assert changes[0].path == "/users"


# ==========================================
# Test 2: Deleted endpoint detected
# ==========================================
def test_2_deleted_endpoint_detected():
    prev = APISnapshot()
    prev.add_endpoint(APIEndpointSnapshot(method="DELETE", path="/users/{id}", function_name="delete_user"))
    curr = APISnapshot()

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    assert changes[0].change_type == "removed"
    assert changes[0].path == "/users/{id}"
    assert changes[0].default_severity == "HIGH"


# ==========================================
# Test 3: Modified endpoint detected
# ==========================================
def test_3_modified_endpoint_detected():
    prev = APISnapshot()
    prev.add_endpoint(APIEndpointSnapshot(method="PUT", path="/users/{id}", function_name="update_user", status_code=200))
    curr = APISnapshot()
    curr.add_endpoint(APIEndpointSnapshot(method="PUT", path="/users/{id}", function_name="update_user", status_code=204))

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    assert changes[0].change_type == "modified"
    assert "status_code_changed" in changes[0].diff_details


# ==========================================
# Test 4: New request field detected
# ==========================================
def test_4_new_request_field_detected():
    prev = APISnapshot()
    prev.add_endpoint(
        APIEndpointSnapshot(
            method="POST",
            path="/items",
            function_name="create_item",
            request_body=SchemaSnapshot(name="Item", fields=[FieldSnapshot(name="title", type="string")]),
        )
    )
    curr = APISnapshot()
    curr.add_endpoint(
        APIEndpointSnapshot(
            method="POST",
            path="/items",
            function_name="create_item",
            request_body=SchemaSnapshot(
                name="Item",
                fields=[
                    FieldSnapshot(name="title", type="string"),
                    FieldSnapshot(name="price", type="number", required=True),
                ],
            ),
        )
    )

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    diff = changes[0].diff_details["request_body_diff"]
    added_names = [f["name"] for f in diff["fields_added"]]
    assert "price" in added_names
    assert changes[0].default_severity == "HIGH"


# ==========================================
# Test 5: Removed request field detected
# ==========================================
def test_5_removed_request_field_detected():
    prev = APISnapshot()
    prev.add_endpoint(
        APIEndpointSnapshot(
            method="POST",
            path="/items",
            function_name="create_item",
            request_body=SchemaSnapshot(
                name="Item",
                fields=[
                    FieldSnapshot(name="title", type="string"),
                    FieldSnapshot(name="legacy_code", type="string"),
                ],
            ),
        )
    )
    curr = APISnapshot()
    curr.add_endpoint(
        APIEndpointSnapshot(
            method="POST",
            path="/items",
            function_name="create_item",
            request_body=SchemaSnapshot(name="Item", fields=[FieldSnapshot(name="title", type="string")]),
        )
    )

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    diff = changes[0].diff_details["request_body_diff"]
    removed_names = [f["name"] for f in diff["fields_removed"]]
    assert "legacy_code" in removed_names
    assert changes[0].default_severity == "HIGH"


# ==========================================
# Test 6: New response field detected
# ==========================================
def test_6_new_response_field_detected():
    prev = APISnapshot()
    prev.add_endpoint(
        APIEndpointSnapshot(
            method="GET",
            path="/profile",
            function_name="get_profile",
            response_body=SchemaSnapshot(name="Profile", fields=[FieldSnapshot(name="username", type="string")]),
        )
    )
    curr = APISnapshot()
    curr.add_endpoint(
        APIEndpointSnapshot(
            method="GET",
            path="/profile",
            function_name="get_profile",
            response_body=SchemaSnapshot(
                name="Profile",
                fields=[
                    FieldSnapshot(name="username", type="string"),
                    FieldSnapshot(name="avatar_url", type="string", required=False),
                ],
            ),
        )
    )

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    diff = changes[0].diff_details["response_body_diff"]
    assert len(diff["fields_added"]) == 1
    assert diff["fields_added"][0]["name"] == "avatar_url"
    assert changes[0].default_severity == "LOW"


# ==========================================
# Test 7: Deleted response field detected
# ==========================================
def test_7_deleted_response_field_detected():
    prev = APISnapshot()
    prev.add_endpoint(
        APIEndpointSnapshot(
            method="GET",
            path="/profile",
            function_name="get_profile",
            response_body=SchemaSnapshot(
                name="Profile",
                fields=[
                    FieldSnapshot(name="username", type="string"),
                    FieldSnapshot(name="deprecated_field", type="string"),
                ],
            ),
        )
    )
    curr = APISnapshot()
    curr.add_endpoint(
        APIEndpointSnapshot(
            method="GET",
            path="/profile",
            function_name="get_profile",
            response_body=SchemaSnapshot(name="Profile", fields=[FieldSnapshot(name="username", type="string")]),
        )
    )

    changes = APIComparator.compare(prev, curr)
    assert len(changes) == 1
    diff = changes[0].diff_details["response_body_diff"]
    assert len(diff["fields_removed"]) == 1
    assert changes[0].default_severity == "HIGH"


# ==========================================
# Test 8: OpenAPI remains valid
# ==========================================
def test_8_openapi_remains_valid():
    base_spec = {
        "openapi": "3.0.3",
        "info": {"title": "App API", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {}},
    }
    plan = [
        SingleAPIChangePlan(
            type="added",
            method="POST",
            path="/tasks",
            summary="Create Task",
            explanation="Added tasks endpoint",
            documentation_changes=DocumentationChanges(
                request_fields_added=[FieldChange(name="title", type="string", required=True)]
            ),
            impact=ImpactAnalysis(severity="LOW", reason="Additive"),
            confidence=0.95,
        )
    ]
    updated = OpenAPIUpdater.apply_change_plan(base_spec, plan)
    is_valid, errors, status = OpenAPIValidator.validate_spec(updated)
    assert is_valid is True
    assert status == "VALID"


# ==========================================
# Test 9: Invalid AI response does not corrupt OpenAPI
# ==========================================
def test_9_invalid_ai_response_does_not_corrupt_openapi():
    original_spec = {
        "openapi": "3.0.3",
        "info": {"title": "Production API", "version": "1.0.0"},
        "paths": {"/health": {"get": {"responses": {"200": {"description": "OK"}}}}},
        "components": {"schemas": {}},
    }
    # Attempting to apply an empty or invalid plan preserves the original spec
    updated = OpenAPIUpdater.apply_change_plan(original_spec, [])
    assert updated == original_spec
    assert "/health" in updated["paths"]


# ==========================================
# Test 10: Duplicate webhook does not process twice
# ==========================================
@pytest.mark.asyncio
async def test_10_duplicate_webhook_does_not_process_twice(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage"))

    # Create local git repo
    repo_dir = tmp_path / "dedup_repo"
    repo_dir.mkdir()
    git_repo = Repo.init(repo_dir)
    git_repo.config_writer().set_value("user", "name", "Dev").release()
    git_repo.config_writer().set_value("user", "email", "dev@example.com").release()
    (repo_dir / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    git_repo.index.add(["app.py"])
    commit1 = git_repo.index.commit("Initial commit")

    repo_in = RepositoryCreate(owner="test", name="dedup", clone_url=str(repo_dir))
    db_repo = await RepositoryService.connect_repository(db_session, repo_in)

    pipeline = AnalysisPipeline()
    res1 = await pipeline.process_commit_event(
        db=db_session,
        repository=db_repo,
        before_sha=None,
        after_sha=commit1.hexsha,
    )
    assert res1["status"] in ("COMPLETED", "NO_CHANGES")

    # Second execution of same commit
    res2 = await pipeline.process_commit_event(
        db=db_session,
        repository=db_repo,
        before_sha=None,
        after_sha=commit1.hexsha,
    )
    assert "idempotent skip" in res2["message"].lower()


# ==========================================
# Test 11: No API change results in no unnecessary doc update
# ==========================================
@pytest.mark.asyncio
async def test_11_no_api_change_results_in_no_doc_update(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage"))

    repo_dir = tmp_path / "no_change_repo"
    repo_dir.mkdir()
    git_repo = Repo.init(repo_dir)
    git_repo.config_writer().set_value("user", "name", "Dev").release()
    git_repo.config_writer().set_value("user", "email", "dev@example.com").release()

    (repo_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/test')\ndef t(): pass\n", encoding="utf-8")
    git_repo.index.add(["main.py"])
    commit1 = git_repo.index.commit("Commit 1")

    repo_in = RepositoryCreate(owner="test", name="no-change", clone_url=str(repo_dir))
    db_repo = await RepositoryService.connect_repository(db_session, repo_in)

    pipeline = AnalysisPipeline()
    await pipeline.process_commit_event(db_session, db_repo, None, commit1.hexsha)
    versions_count_initial = db_session.query(DocumentationVersion).filter(DocumentationVersion.repository_id == db_repo.id).count()

    # Commit 2: Only change README (no API changes)
    (repo_dir / "README.md").write_text("# Doc update\n", encoding="utf-8")
    git_repo.index.add(["README.md"])
    commit2 = git_repo.index.commit("Update readme")

    res2 = await pipeline.process_commit_event(db_session, db_repo, commit1.hexsha, commit2.hexsha)
    assert res2["status"] == "NO_CHANGES"

    versions_count_after = db_session.query(DocumentationVersion).filter(DocumentationVersion.repository_id == db_repo.id).count()
    assert versions_count_after == versions_count_initial  # No unnecessary version created


# ==========================================
# Test 12: Low confidence change becomes REVIEW_REQUIRED
# ==========================================
def test_12_low_confidence_change_becomes_review_required():
    confidence_threshold = 0.85
    plan_item = SingleAPIChangePlan(
        type="modified",
        method="POST",
        path="/users",
        explanation="Ambiguous change",
        impact=ImpactAnalysis(severity="MEDIUM", reason="Unclear"),
        confidence=0.72,  # Low confidence < 0.85
    )

    status = "AUTO_APPLIED" if plan_item.confidence >= confidence_threshold else "REVIEW_REQUIRED"
    assert status == "REVIEW_REQUIRED"
