"""Tests for Repository API endpoints."""


def test_create_and_get_repository(client):
    """Test connecting a new repository and reading it back."""
    payload = {
        "owner": "fastapi-org",
        "name": "sample-backend",
        "default_branch": "main",
        "framework": "fastapi",
        "confidence_threshold": 0.85,
    }
    response = client.post("/repositories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["owner"] == "fastapi-org"
    assert data["name"] == "sample-backend"
    assert data["full_name"] == "fastapi-org/sample-backend"
    assert data["clone_url"] == "https://github.com/fastapi-org/sample-backend.git"
    assert data["status"] == "IDLE"
    assert data["api_changes_count"] == 0

    repo_id = data["id"]

    # Read back single repository
    detail_res = client.get(f"/repositories/{repo_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == repo_id
    assert detail_data["name"] == "sample-backend"
    assert "recent_commits" in detail_data
    assert "recent_changes" in detail_data


def test_duplicate_repository_conflict(client):
    """Test connecting duplicate repository returns 409 conflict."""
    payload = {
        "owner": "octocat",
        "name": "hello-world",
    }
    res1 = client.post("/repositories", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/repositories", json=payload)
    assert res2.status_code == 409
    assert "already connected" in res2.json()["detail"]


def test_list_repositories(client):
    """Test listing repositories."""
    client.post("/repositories", json={"owner": "user1", "name": "repo1"})
    client.post("/repositories", json={"owner": "user2", "name": "repo2"})

    response = client.get("/repositories")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2
    names = [r["name"] for r in items]
    assert "repo1" in names
    assert "repo2" in names


def test_update_repository(client):
    """Test updating repository configurations."""
    res = client.post("/repositories", json={"owner": "org", "name": "app"})
    repo_id = res.json()["id"]

    update_payload = {
        "confidence_threshold": 0.92,
        "default_branch": "develop",
        "openapi_path": "docs/openapi.yaml",
    }
    update_res = client.put(f"/repositories/{repo_id}", json=update_payload)
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["confidence_threshold"] == 0.92
    assert data["default_branch"] == "develop"
    assert data["openapi_path"] == "docs/openapi.yaml"


def test_delete_repository(client):
    """Test deleting a repository."""
    res = client.post("/repositories", json={"owner": "delete-me", "name": "temporary"})
    repo_id = res.json()["id"]

    del_res = client.delete(f"/repositories/{repo_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/repositories/{repo_id}")
    assert get_res.status_code == 404


def test_get_nonexistent_repository(client):
    """Test 404 for invalid repository ID."""
    response = client.get("/repositories/99999")
    assert response.status_code == 404


def test_repository_documentation_summary_empty(client):
    """Test documentation summary endpoint when no docs generated yet."""
    res = client.post("/repositories", json={"owner": "doc-org", "name": "new-api"})
    repo_id = res.json()["id"]

    doc_res = client.get(f"/repositories/{repo_id}/documentation")
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    assert doc_data["repository_id"] == repo_id
    assert doc_data["total_versions"] == 0
    assert doc_data["latest_version"] is None
    assert doc_data["endpoints_count"] == 0


def test_repository_changes_empty(client):
    """Test changes list for repository with no changes yet."""
    res = client.post("/repositories", json={"owner": "changes-org", "name": "fresh-api"})
    repo_id = res.json()["id"]

    changes_res = client.get(f"/repositories/{repo_id}/changes")
    assert changes_res.status_code == 200
    assert changes_res.json() == []
