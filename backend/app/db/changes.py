"""Database operations for API Changes."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.api_change import APIChange
from app.schemas.changes import APIChangeCreate


def get_changes_by_repository(
    db: Session,
    repository_id: int,
    skip: int = 0,
    limit: int = 100,
    change_type: Optional[str] = None
) -> List[APIChange]:
    """Retrieve list of API changes for a repository."""
    query = db.query(APIChange).filter(APIChange.repository_id == repository_id)
    if change_type:
        query = query.filter(APIChange.change_type == change_type)
    return query.order_by(APIChange.created_at.desc()).offset(skip).limit(limit).all()


def get_change_by_id(db: Session, change_id: int) -> Optional[APIChange]:
    """Retrieve single API change by ID."""
    return db.query(APIChange).filter(APIChange.id == change_id).first()


def create_api_change(db: Session, change_in: APIChangeCreate) -> APIChange:
    """Create a new API change record."""
    db_change = APIChange(
        repository_id=change_in.repository_id,
        commit_id=change_in.commit_id,
        change_type=change_in.change_type,
        method=change_in.method,
        path=change_in.path,
        summary=change_in.summary,
        old_structure=change_in.old_structure,
        new_structure=change_in.new_structure,
        ai_explanation=change_in.ai_explanation,
        impact_analysis=change_in.impact_analysis,
        confidence=change_in.confidence,
        status=change_in.status,
        source_file=change_in.source_file,
        source_line=change_in.source_line,
    )
    db.add(db_change)
    db.commit()
    db.refresh(db_change)
    return db_change
