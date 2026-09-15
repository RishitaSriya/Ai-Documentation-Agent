"""GitHub Webhook receiver for push events with HMAC-SHA256 signature verification."""

import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger, log_pipeline_event
from app.core.security import verify_github_signature
from app.db.database import get_db, SessionLocal
from app.db import repositories as repo_db
from app.services.pipeline.analysis_pipeline import AnalysisPipeline
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def run_pipeline_background(
    repo_id: int,
    before_sha: Optional[str],
    after_sha: str,
    commit_msg: Optional[str] = None,
    commit_author: Optional[str] = None
) -> None:
    """Execute analysis pipeline asynchronously in the background."""
    db = SessionLocal()
    try:
        repo = repo_db.get_repository_by_id(db, repo_id)
        if not repo:
            logger.error(f"Background pipeline: Repository {repo_id} not found.")
            return

        # Pull latest Git changes
        try:
            await RepositoryService.sync_repository(db, repo_id)
        except Exception as e:
            logger.warning(f"Background sync warning for repo {repo_id}: {str(e)}")

        pipeline = AnalysisPipeline()
        result = await pipeline.process_commit_event(
            db=db,
            repository=repo,
            before_sha=before_sha,
            after_sha=after_sha,
            commit_message=commit_msg,
            commit_author=commit_author,
        )
        logger.info(f"Background pipeline completed for repo {repo.full_name}: {result}")
    except Exception as e:
        logger.error(f"Background pipeline error for repo {repo_id}: {str(e)}", exc_info=True)
    finally:
        db.close()


@router.post("/github", summary="GitHub Webhook Receiver")
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header("push"),
    db: Session = Depends(get_db)
):
    """Handle incoming GitHub webhook push events."""
    body_bytes = await request.body()

    # 1. Verify HMAC SHA-256 signature if secret is configured
    if settings.GITHUB_WEBHOOK_SECRET:
        if not verify_github_signature(body_bytes, settings.GITHUB_WEBHOOK_SECRET, x_hub_signature_256):
            log_pipeline_event("WEBHOOK", "Signature verification failed", level=30)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature."
            )

    # 2. Parse payload
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.")

    # 3. Handle Ping Event
    if x_github_event == "ping":
        log_pipeline_event("WEBHOOK", "Received GitHub ping event.")
        return {"status": "pong", "zen": payload.get("zen")}

    # 4. Handle Push Event
    if x_github_event != "push":
        return {"status": "ignored", "event": x_github_event}

    repo_data = payload.get("repository", {})
    owner = repo_data.get("owner", {}).get("login") or repo_data.get("owner", {}).get("name")
    repo_name = repo_data.get("name")

    if not owner or not repo_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository information missing in webhook.")

    # Look up connected repository
    repo = repo_db.get_repository_by_owner_and_name(db, owner, repo_name)
    if not repo:
        log_pipeline_event("WEBHOOK", f"Repository {owner}/{repo_name} is not connected. Ignoring webhook.")
        return {"status": "ignored", "message": f"Repository {owner}/{repo_name} not registered."}

    before_sha = payload.get("before")
    after_sha = payload.get("after") or payload.get("head_commit", {}).get("id")

    if not after_sha:
        return {"status": "ignored", "message": "No commit SHA in push event."}

    head_commit = payload.get("head_commit", {})
    commit_msg = head_commit.get("message")
    commit_author = head_commit.get("author", {}).get("name")

    log_pipeline_event("WEBHOOK", f"Received push event for {repo.full_name} ({after_sha[:7]})", repo=repo.full_name, commit=after_sha)

    # Schedule background processing
    background_tasks.add_task(
        run_pipeline_background,
        repo_id=repo.id,
        before_sha=before_sha,
        after_sha=after_sha,
        commit_msg=commit_msg,
        commit_author=commit_author,
    )

    return {
        "status": "queued",
        "repository": repo.full_name,
        "commit_sha": after_sha,
        "message": "API analysis pipeline queued for background processing."
    }
