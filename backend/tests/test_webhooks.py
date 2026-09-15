"""Tests for GitHub webhook handler."""

import hmac
import hashlib
import json


def test_webhook_ping(client):
    """Test webhook responds to ping events."""
    headers = {"X-GitHub-Event": "ping"}
    payload = {"zen": "Mind your words, they are important."}
    response = client.post("/webhooks/github", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "pong"


def test_webhook_push_for_connected_repo(client):
    """Test webhook handles push events for registered repositories."""
    # Connect repository first
    client.post("/repositories", json={"owner": "octo-org", "name": "webhook-api"})

    payload = {
        "repository": {
            "owner": {"login": "octo-org"},
            "name": "webhook-api",
        },
        "before": "0000000000000000000000000000000000000000",
        "after": "112233445566778899aabbccddeeff0011223344",
        "head_commit": {
            "id": "112233445566778899aabbccddeeff0011223344",
            "message": "Add endpoints",
            "author": {"name": "Octocat"},
        },
    }

    headers = {"X-GitHub-Event": "push"}
    response = client.post("/webhooks/github", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert data["commit_sha"] == "112233445566778899aabbccddeeff0011223344"


def test_webhook_unregistered_repo_ignored(client):
    """Test push events for unregistered repos are ignored gracefully."""
    payload = {
        "repository": {
            "owner": {"login": "unknown-org"},
            "name": "unknown-repo",
        },
        "after": "abcdef1234567890",
    }
    response = client.post("/webhooks/github", json=payload, headers={"X-GitHub-Event": "push"})
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
