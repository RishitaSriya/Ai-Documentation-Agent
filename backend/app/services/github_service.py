"""GitHub REST API integration service."""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger


class GitHubService:
    """Service for interacting with the GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN

    @property
    def headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-API-Doc-Agent",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata from GitHub with graceful fallback."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        fallback_data = {
            "github_repo_id": None,
            "owner": owner,
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "default_branch": "main",
            "clone_url": f"https://github.com/{owner}/{repo}.git",
            "description": None,
            "is_private": False,
        }

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "github_repo_id": str(data.get("id")),
                        "owner": data.get("owner", {}).get("login", owner),
                        "name": data.get("name", repo),
                        "full_name": data.get("full_name", f"{owner}/{repo}"),
                        "default_branch": data.get("default_branch", "main"),
                        "clone_url": data.get("clone_url", f"https://github.com/{owner}/{repo}.git"),
                        "description": data.get("description"),
                        "is_private": data.get("private", False),
                    }
                elif response.status_code == 401:
                    logger.warning(f"GitHub authentication failed for {owner}/{repo}. Using default metadata.")
                    return fallback_data
                elif response.status_code == 403:
                    logger.warning(f"GitHub API rate limit exceeded or access forbidden. Falling back to default metadata.")
                    return fallback_data
                elif response.status_code == 404:
                    logger.info(f"Repository {owner}/{repo} not found on remote GitHub or is local. Using standard configuration.")
                    return fallback_data
                else:
                    logger.warning(f"GitHub API returned status {response.status_code}. Using fallback metadata.")
                    return fallback_data
        except Exception as e:
            logger.warning(f"Failed to communicate with GitHub API: {str(e)}. Using fallback metadata.")
            return fallback_data

    async def list_branches(self, owner: str, repo: str) -> List[str]:
        """List repository branches with fallback."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/branches"
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return [b["name"] for b in response.json()]
        except Exception as e:
            logger.warning(f"Failed to list branches for {owner}/{repo}: {str(e)}")
        return ["main"]

    async def get_latest_commit(self, owner: str, repo: str, branch: str = "main") -> Optional[Dict[str, Any]]:
        """Fetch latest commit on a branch with fallback."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{branch}"
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "sha": data["sha"],
                        "message": data["commit"]["message"],
                        "author": f"{data['commit']['author']['name']} <{data['commit']['author']['email']}>",
                        "timestamp": data["commit"]["author"]["date"],
                    }
        except Exception as e:
            logger.warning(f"Failed to get latest commit for {owner}/{repo}: {str(e)}")
        return None
