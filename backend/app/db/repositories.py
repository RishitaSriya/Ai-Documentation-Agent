"""Database operations for repositories."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.repository import Repository
from app.models.api_change import APIChange
from app.models.documentation_version import DocumentationVersion
from app.schemas.repository import RepositoryCreate, RepositoryUpdate


def get_repositories(db: Session, skip: int = 0, limit: int = 100) -> List[Repository]:
    """List repositories with pagination."""
    return db.query(Repository).order_by(Repository.updated_at.desc()).offset(skip).limit(limit).all()


def get_repository_by_id(db: Session, repo_id: int) -> Optional[Repository]:
    """Retrieve repository by primary ID."""
    return db.query(Repository).filter(Repository.id == repo_id).first()


def get_repository_by_owner_and_name(db: Session, owner: str, name: str) -> Optional[Repository]:
    """Retrieve repository by owner and name."""
    return db.query(Repository).filter(
        func.lower(Repository.owner) == owner.lower(),
        func.lower(Repository.name) == name.lower()
    ).first()


def create_repository(db: Session, repo_in: RepositoryCreate) -> Repository:
    """Create a new repository record."""
    clone_url = repo_in.clone_url or f"https://github.com/{repo_in.owner}/{repo_in.name}.git"

    db_repo = Repository(
        owner=repo_in.owner,
        name=repo_in.name,
        default_branch=repo_in.default_branch or "main",
        clone_url=str(clone_url),
        framework=repo_in.framework or "fastapi",
        source_root=repo_in.source_root or "",
        openapi_path=repo_in.openapi_path or "",
        auto_publish=repo_in.auto_publish,
        confidence_threshold=repo_in.confidence_threshold,
        status="IDLE",
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    return db_repo


def update_repository(db: Session, db_repo: Repository, repo_update: RepositoryUpdate) -> Repository:
    """Update repository fields."""
    update_data = repo_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_repo, field, value)

    db.commit()
    db.refresh(db_repo)
    return db_repo


def delete_repository(db: Session, db_repo: Repository) -> None:
    """Delete a repository and cascaded records."""
    db.delete(db_repo)
    db.commit()


def get_repository_metrics(db: Session, repo_id: int) -> dict:
    """Get calculated metrics for a repository (changes count, latest doc version)."""
    changes_count = db.query(func.count(APIChange.id)).filter(APIChange.repository_id == repo_id).scalar() or 0
    latest_version = db.query(func.max(DocumentationVersion.version)).filter(DocumentationVersion.repository_id == repo_id).scalar()

    return {
        "api_changes_count": changes_count,
        "latest_documentation_version": latest_version,
    }
