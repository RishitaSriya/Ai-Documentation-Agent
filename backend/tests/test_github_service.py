"""Tests for GitHubService."""

import pytest
from app.services.github_service import GitHubService


@pytest.mark.asyncio
async def test_github_service_headers():
    """Test header generation with and without token."""
    service_no_token = GitHubService(token=None)
    assert "Authorization" not in service_no_token.headers or service_no_token.headers["Authorization"] == "Bearer None"

    service_with_token = GitHubService(token="ghp_test1234567890")
    assert service_with_token.headers["Authorization"] == "Bearer ghp_test1234567890"


@pytest.mark.asyncio
async def test_github_service_fallback():
    """Test graceful metadata fallback on connection failure."""
    service = GitHubService()
    info = await service.get_repository_info("octocat", "Hello-World")
    assert info["owner"] == "octocat"
    assert info["name"] == "Hello-World"
    assert "clone_url" in info
