"""Repository management API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import repositories as repo_db
from app.db import changes as changes_db
from app.db import documentation as doc_db
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryDetailResponse,
)
from app.schemas.changes import APIChangeResponse
from app.schemas.documentation import DocumentationSummaryResponse
from app.services.pipeline.analysis_pipeline import AnalysisPipeline
from app.services.repository_service import RepositoryService
from app.core.logging import log_pipeline_event

router = APIRouter(prefix="/repositories", tags=["Repositories"])


def _to_repo_response(repo, db: Session) -> RepositoryResponse:
    """Enrich repository model with computed metrics."""
    metrics = repo_db.get_repository_metrics(db, repo.id)
    return RepositoryResponse(
        id=repo.id,
        github_repo_id=repo.github_repo_id,
        owner=repo.owner,
        name=repo.name,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        clone_url=repo.clone_url,
        webhook_id=repo.webhook_id,
        framework=repo.framework,
        source_root=repo.source_root,
        openapi_path=repo.openapi_path,
        auto_publish=repo.auto_publish,
        confidence_threshold=repo.confidence_threshold,
        status=repo.status,
        last_processed_commit=repo.last_processed_commit,
        api_changes_count=metrics["api_changes_count"],
        latest_documentation_version=metrics["latest_documentation_version"],
        created_at=repo.created_at,
        updated_at=repo.updated_at,
    )


@router.get("", response_model=List[RepositoryResponse], summary="List connected repositories")
def list_repositories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all connected GitHub repositories."""
    repos = repo_db.get_repositories(db, skip=skip, limit=limit)
    return [_to_repo_response(r, db) for r in repos]


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED, summary="Connect repository")
async def create_repository(repo_in: RepositoryCreate, db: Session = Depends(get_db)):
    """Connect a new GitHub repository."""
    existing = repo_db.get_repository_by_owner_and_name(db, repo_in.owner, repo_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository {repo_in.owner}/{repo_in.name} is already connected."
        )

    try:
        repo = await RepositoryService.connect_repository(db, repo_in)
        return _to_repo_response(repo, db)
    except Exception as e:
        log_pipeline_event("REPOSITORY", f"Connection error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{repo_id}", response_model=RepositoryDetailResponse, summary="Get repository details")
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    """Get detailed information for a single repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    base_resp = _to_repo_response(repo, db)
    
    recent_commits = [
        {
            "id": c.id,
            "commit_sha": c.commit_sha,
            "message": c.message,
            "author": c.author,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in (repo.commits[:10] if repo.commits else [])
    ]

    recent_changes = [
        {
            "id": ch.id,
            "change_type": ch.change_type,
            "method": ch.method,
            "path": ch.path,
            "summary": ch.summary,
            "confidence": ch.confidence,
            "status": ch.status,
            "created_at": ch.created_at.isoformat() if ch.created_at else None,
        }
        for ch in (repo.api_changes[:15] if repo.api_changes else [])
    ]

    return RepositoryDetailResponse(
        **base_resp.model_dump(),
        recent_commits=recent_commits,
        recent_changes=recent_changes,
    )


@router.post("/{repo_id}/sync", response_model=RepositoryResponse, summary="Sync repository with remote")
async def sync_repository(repo_id: int, db: Session = Depends(get_db)):
    """Fetch and pull latest changes from the remote Git repository."""
    try:
        repo = await RepositoryService.sync_repository(db, repo_id)
        return _to_repo_response(repo, db)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{repo_id}/analyze", summary="Trigger manual repository API analysis")
async def trigger_repository_analysis(
    repo_id: int,
    commit_sha: Optional[str] = Query(None, description="Optional commit SHA to analyze"),
    force: bool = Query(False, description="Force re-analysis even if commit already processed"),
    db: Session = Depends(get_db)
):
    """Trigger the end-to-end API analysis pipeline manually."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    pipeline = AnalysisPipeline()
    try:
        result = await pipeline.process_repository_analysis(
            db=db,
            repository_id=repo_id,
            commit_sha=commit_sha,
            force=force,
        )
        return result
    except Exception as e:
        log_pipeline_event("PIPELINE", f"Manual analysis error: {str(e)}", level=40)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{repo_id}", response_model=RepositoryResponse, summary="Update repository settings")
def update_repository(repo_id: int, repo_update: RepositoryUpdate, db: Session = Depends(get_db)):
    """Update settings for a connected repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    updated = repo_db.update_repository(db, repo, repo_update)
    return _to_repo_response(updated, db)


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Disconnect repository")
def delete_repository(repo_id: int, db: Session = Depends(get_db)):
    """Disconnect and remove a repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    repo_db.delete_repository(db, repo)
    return None


@router.get("/{repo_id}/changes", response_model=List[APIChangeResponse], summary="List repository API changes")
def get_repository_changes(repo_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve API change history for a repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    changes = changes_db.get_changes_by_repository(db, repo_id, skip=skip, limit=limit)
    return [
        APIChangeResponse(
            id=c.id,
            repository_id=c.repository_id,
            commit_id=c.commit_id,
            commit_sha=c.commit.commit_sha if c.commit else None,
            change_type=c.change_type,
            method=c.method,
            path=c.path,
            summary=c.summary,
            old_structure=c.old_structure,
            new_structure=c.new_structure,
            ai_explanation=c.ai_explanation,
            impact_analysis=c.impact_analysis,
            confidence=c.confidence,
            status=c.status,
            source_file=c.source_file,
            source_line=c.source_line,
            created_at=c.created_at,
        )
        for c in changes
    ]


@router.get("/{repo_id}/documentation", response_model=DocumentationSummaryResponse, summary="Get documentation summary")
def get_repository_documentation_summary(repo_id: int, db: Session = Depends(get_db)):
    """Retrieve OpenAPI documentation summary and links for a repository."""
    repo = repo_db.get_repository_by_id(db, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    latest_doc = doc_db.get_latest_documentation_version(db, repo_id)
    all_docs = doc_db.get_documentation_versions(db, repo_id)

    endpoints_count = 0
    if latest_doc and isinstance(latest_doc.openapi_json, dict):
        paths = latest_doc.openapi_json.get("paths", {})
        for _, path_item in paths.items():
            if isinstance(path_item, dict):
                endpoints_count += len([m for m in path_item.keys() if m.lower() in ["get", "post", "put", "delete", "patch", "options", "head"]])

    return DocumentationSummaryResponse(
        repository_id=repo_id,
        latest_version=latest_doc.version if latest_doc else None,
        validation_status=latest_doc.validation_status if latest_doc else None,
        total_versions=len(all_docs),
        endpoints_count=endpoints_count,
        openapi_url=f"/repositories/{repo_id}/openapi.json",
        docs_url=f"/repositories/{repo_id}/docs",
    )
