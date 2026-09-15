"""API Change exploration and detail endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import repositories as repo_db
from app.db import changes as changes_db
from app.schemas.changes import APIChangeResponse

router = APIRouter(prefix="/repositories", tags=["Changes"])


@router.get("/{repo_id}/changes/{change_id}", response_model=APIChangeResponse, summary="Get single API change detail")
def get_change_detail(repo_id: int, change_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed before/after diff and AI reasoning for a single change."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    change = changes_db.get_change_by_id(db, change_id)
    if not change or change.repository_id != repo_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Change not found")

    return APIChangeResponse(
        id=change.id,
        repository_id=change.repository_id,
        commit_id=change.commit_id,
        commit_sha=change.commit.commit_sha if change.commit else None,
        change_type=change.change_type,
        method=change.method,
        path=change.path,
        summary=change.summary,
        old_structure=change.old_structure,
        new_structure=change.new_structure,
        ai_explanation=change.ai_explanation,
        impact_analysis=change.impact_analysis,
        confidence=change.confidence,
        status=change.status,
        source_file=change.source_file,
        source_line=change.source_line,
        created_at=change.created_at,
    )
