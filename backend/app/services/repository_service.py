"""Repository orchestration service connecting GitHub and Git operations."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger, log_pipeline_event
from app.models.repository import Repository
from app.models.commit import Commit
from app.schemas.repository import RepositoryCreate
from app.services.git_service import GitService
from app.services.github_service import GitHubService
from app.db import repositories as repo_db


class RepositoryService:
    """Orchestrates repository lifecycle, cloning, and metadata tracking."""

    @staticmethod
    def get_repo_local_path(owner: str, name: str) -> Path:
        """Compute local disk directory for a cloned repository."""
        return settings.repositories_storage_dir / owner / name

    @classmethod
    async def connect_repository(
        cls,
        db: Session,
        repo_in: RepositoryCreate,
        github_token: Optional[str] = None
    ) -> Repository:
        """Connect, fetch metadata, clone locally, and record initial state."""
        log_pipeline_event("REPOSITORY", f"Starting connection flow for {repo_in.owner}/{repo_in.name}")

        # 1. Fetch metadata from GitHub API
        github_service = GitHubService(token=github_token)
        gh_info = await github_service.get_repository_info(repo_in.owner, repo_in.name)

        # Merge with user provided overrides
        default_branch = repo_in.default_branch or gh_info.get("default_branch") or "main"
        clone_url = repo_in.clone_url or gh_info.get("clone_url")
        github_repo_id = gh_info.get("github_repo_id")

        local_path = cls.get_repo_local_path(repo_in.owner, repo_in.name)

        # 2. Clone repository locally if not already cloned
        head_sha: Optional[str] = None
        commit_info: Optional[dict] = None

        if not (local_path / ".git").exists():
            log_pipeline_event("GIT", f"Cloning remote repository into {local_path}")
            try:
                GitService.clone_repository(
                    clone_url=clone_url,
                    target_path=local_path,
                    branch=default_branch,
                    token=github_token or settings.GITHUB_TOKEN,
                )
            except Exception as e:
                logger.warning(f"Remote clone failed ({str(e)}). Checking if local path already has files.")
                if not local_path.exists():
                    local_path.mkdir(parents=True, exist_ok=True)

        if (local_path / ".git").exists():
            try:
                commit_info = GitService.get_commit_info(local_path)
                head_sha = commit_info["sha"]
            except Exception as e:
                logger.warning(f"Could not read commit info from {local_path}: {str(e)}")

        # 3. Create repository record in DB
        db_repo = Repository(
            github_repo_id=github_repo_id,
            owner=repo_in.owner,
            name=repo_in.name,
            default_branch=default_branch,
            clone_url=clone_url,
            framework=repo_in.framework or "fastapi",
            source_root=repo_in.source_root or "",
            openapi_path=repo_in.openapi_path or "",
            auto_publish=repo_in.auto_publish,
            confidence_threshold=repo_in.confidence_threshold,
            status="SYNCED" if head_sha else "IDLE",
            last_processed_commit=head_sha,
        )
        db.add(db_repo)
        db.commit()
        db.refresh(db_repo)

        # 4. Record initial commit if available
        if commit_info and head_sha:
            db_commit = Commit(
                repository_id=db_repo.id,
                commit_sha=head_sha,
                parent_sha=commit_info.get("parent_sha"),
                message=commit_info.get("message"),
                author=commit_info.get("author"),
                timestamp=commit_info.get("timestamp"),
                status="COMPLETED",
            )
            db.add(db_commit)
            db.commit()

        log_pipeline_event("REPOSITORY", f"Repository {db_repo.full_name} successfully registered (ID: {db_repo.id})")
        return db_repo

    @classmethod
    async def sync_repository(cls, db: Session, repo_id: int) -> Repository:
        """Pull latest changes from remote Git and record new commits."""
        repo = repo_db.get_repository_by_id(db, repo_id)
        if not repo:
            raise ValueError(f"Repository with ID {repo_id} not found.")

        local_path = cls.get_repo_local_path(repo.owner, repo.name)
        if not (local_path / ".git").exists():
            raise RuntimeError(f"Local repository clone not found at {local_path}.")

        log_pipeline_event("GIT", f"Syncing repository {repo.full_name}")
        head_sha = GitService.fetch_and_pull(local_path, branch=repo.default_branch)

        commit_info = GitService.get_commit_info(local_path, head_sha)

        # Check if commit already recorded
        existing_commit = db.query(Commit).filter(
            Commit.repository_id == repo.id,
            Commit.commit_sha == head_sha
        ).first()

        if not existing_commit:
            new_commit = Commit(
                repository_id=repo.id,
                commit_sha=head_sha,
                parent_sha=commit_info.get("parent_sha"),
                message=commit_info.get("message"),
                author=commit_info.get("author"),
                timestamp=commit_info.get("timestamp"),
                status="PENDING",
            )
            db.add(new_commit)

        repo.last_processed_commit = head_sha
        repo.status = "SYNCED"
        repo.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(repo)

        return repo
