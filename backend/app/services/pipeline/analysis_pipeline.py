"""Central Analysis Pipeline coordinating Git, AST Analysis, AI Agent, OpenAPI, and DB."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger, log_pipeline_event
from app.db import repositories as repo_db
from app.db import changes as changes_db
from app.models.repository import Repository
from app.models.commit import Commit
from app.models.agent_run import AgentRun
from app.schemas.changes import APIChangeCreate
from app.services.ai.agent import AIAgent
from app.services.change_detector import ChangeDetector
from app.services.git_service import GitService
from app.services.openapi.loader import OpenAPILoader
from app.services.openapi.updater import OpenAPIUpdater
from app.services.openapi.validator import OpenAPIValidator
from app.services.openapi.publisher import OpenAPIPublisher
from app.services.repository_service import RepositoryService


class AnalysisPipeline:
    """End-to-End Orchestrator for analyzing code commits, updating OpenAPI, and persisting changes."""

    def __init__(
        self,
        change_detector: Optional[ChangeDetector] = None,
        ai_agent: Optional[AIAgent] = None
    ):
        self.change_detector = change_detector or ChangeDetector()
        self.ai_agent = ai_agent or AIAgent()

    async def process_repository_analysis(
        self,
        db: Session,
        repository_id: int,
        commit_sha: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Run analysis on a repository's current HEAD commit or specified commit."""
        repo = repo_db.get_repository_by_id(db, repository_id)
        if not repo:
            raise ValueError(f"Repository {repository_id} not found.")

        repo_path = RepositoryService.get_repo_local_path(repo.owner, repo.name)
        if not (repo_path / ".git").exists():
            raise RuntimeError(f"Local clone not available at {repo_path}. Please sync or connect first.")

        # Determine target commit SHA
        commit_info = GitService.get_commit_info(repo_path, commit_sha)
        target_sha = commit_info["sha"]
        parent_sha = commit_info.get("parent_sha") or repo.last_processed_commit

        return await self.process_commit_event(
            db=db,
            repository=repo,
            before_sha=parent_sha if parent_sha != target_sha else None,
            after_sha=target_sha,
            commit_message=commit_info.get("message"),
            commit_author=commit_info.get("author"),
            commit_timestamp=commit_info.get("timestamp"),
            force=force,
        )

    async def process_commit_event(
        self,
        db: Session,
        repository: Repository,
        before_sha: Optional[str],
        after_sha: str,
        commit_message: Optional[str] = None,
        commit_author: Optional[str] = None,
        commit_timestamp: Optional[datetime] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Execute full pipeline for a commit push or analysis trigger."""
        repo_id = repository.id
        repo_name = repository.full_name
        repo_path = RepositoryService.get_repo_local_path(repository.owner, repository.name)

        log_pipeline_event("PIPELINE", f"Processing commit {after_sha[:7]} for {repo_name}", repo=repo_name, commit=after_sha)

        # 1. Idempotency Check: Prevent duplicate processing of same commit
        existing_commit = db.query(Commit).filter(
            Commit.repository_id == repo_id,
            Commit.commit_sha == after_sha
        ).first()

        if existing_commit and existing_commit.status in ("COMPLETED", "NO_CHANGES") and not force:
            logger.info(f"Commit {after_sha[:7]} already processed with status {existing_commit.status}. Skipping.")
            return {
                "status": existing_commit.status,
                "message": "Commit already processed (idempotent skip).",
                "commit_sha": after_sha,
                "api_changes": [],
            }

        # Create or update Commit record
        if not existing_commit:
            existing_commit = Commit(
                repository_id=repo_id,
                commit_sha=after_sha,
                parent_sha=before_sha,
                message=commit_message,
                author=commit_author,
                timestamp=commit_timestamp or datetime.now(timezone.utc),
                status="PROCESSING",
            )
            db.add(existing_commit)
            db.commit()
            db.refresh(existing_commit)
        else:
            existing_commit.status = "PROCESSING"
            db.commit()

        repository.status = "PROCESSING"
        db.commit()

        try:
            # 2. Change Detection (Git Diff + AST Snapshots + Comparator)
            detection_result = self.change_detector.detect_changes(
                repository_path=repo_path,
                before_sha=before_sha,
                after_sha=after_sha
            )

            detected_changes = detection_result["api_changes"]
            curr_snapshot = detection_result["curr_snapshot"]

            # 3. Retrieve or generate baseline OpenAPI
            current_openapi = OpenAPIPublisher.get_current_openapi(repo_id, db)
            if not current_openapi:
                # Search repo or generate baseline
                existing_file_spec = OpenAPILoader.find_and_load(repo_path, repository.openapi_path)
                if existing_file_spec:
                    current_openapi = existing_file_spec
                else:
                    current_openapi = OpenAPILoader.generate_baseline(
                        curr_snapshot,
                        title=f"{repository.name} API",
                        version="1.0.0"
                    )
                # Save initial baseline version
                OpenAPIPublisher.publish_version(
                    db=db,
                    repo_id=repo_id,
                    openapi_spec=current_openapi,
                    commit_id=existing_commit.id,
                    validation_status="VALID"
                )

            # 4. If No API Changes detected
            if not detected_changes:
                log_pipeline_event("PIPELINE", f"No API changes detected in commit {after_sha[:7]}", repo=repo_name)
                existing_commit.status = "NO_CHANGES"
                repository.status = "SYNCED"
                repository.last_processed_commit = after_sha
                db.commit()
                return {
                    "status": "NO_CHANGES",
                    "message": "No structural API changes detected in commit.",
                    "commit_sha": after_sha,
                    "api_changes": [],
                }

            # 5. Semantic Reasoning with AI Agent
            ai_plan, run_meta = await self.ai_agent.analyze_changes(
                detected_changes=detected_changes,
                git_diff=detection_result["git_diff_text"],
                existing_openapi=current_openapi,
            )

            # Record AgentRun in database
            agent_run = AgentRun(
                repository_id=repo_id,
                commit_id=existing_commit.id,
                input_data=run_meta["input_data"],
                output_data=run_meta["output_data"],
                model=run_meta["model"],
                status=run_meta["status"],
                error=run_meta["error"],
            )
            db.add(agent_run)
            db.commit()

            # 6. Apply Deterministic OpenAPI Updates
            updated_openapi = OpenAPIUpdater.apply_change_plan(
                base_openapi=current_openapi,
                change_plan=ai_plan.changes
            )

            # 7. Validate Updated OpenAPI Specification
            is_valid, val_errors, val_status = OpenAPIValidator.validate_spec(updated_openapi)

            # 8. Determine change statuses and auto-publish
            created_changes = []
            should_publish = is_valid and repository.auto_publish

            for change_plan_item in ai_plan.changes:
                # Find matching detected change to attach source line/file
                matching_detected = next(
                    (c for c in detected_changes if c.method.upper() == change_plan_item.method.upper() and c.path == change_plan_item.path),
                    None
                )

                # Confidence threshold check
                if change_plan_item.confidence < repository.confidence_threshold:
                    change_status = "REVIEW_REQUIRED"
                    should_publish = False
                elif not is_valid:
                    change_status = "FAILED"
                else:
                    change_status = "AUTO_APPLIED"

                change_create = APIChangeCreate(
                    repository_id=repo_id,
                    commit_id=existing_commit.id,
                    change_type=change_plan_item.type,
                    method=change_plan_item.method.upper(),
                    path=change_plan_item.path,
                    summary=change_plan_item.summary,
                    old_structure=matching_detected.old_structure if matching_detected else None,
                    new_structure=matching_detected.new_structure if matching_detected else None,
                    ai_explanation=change_plan_item.explanation,
                    impact_analysis=change_plan_item.impact.model_dump(),
                    confidence=change_plan_item.confidence,
                    status=change_status,
                    source_file=matching_detected.source_file if matching_detected else None,
                    source_line=matching_detected.source_line if matching_detected else None,
                )
                db_change = changes_db.create_api_change(db, change_create)
                created_changes.append(db_change)

            # 9. Publish if valid and approved
            if should_publish:
                OpenAPIPublisher.publish_version(
                    db=db,
                    repo_id=repo_id,
                    openapi_spec=updated_openapi,
                    commit_id=existing_commit.id,
                    validation_status=val_status,
                )

            # 10. Update commit and repository records
            existing_commit.status = "COMPLETED" if is_valid else "FAILED"
            repository.status = "SYNCED" if is_valid else "FAILED"
            repository.last_processed_commit = after_sha
            repository.updated_at = datetime.now(timezone.utc)
            db.commit()

            log_pipeline_event(
                "PIPELINE",
                f"Successfully processed {len(created_changes)} API changes for commit {after_sha[:7]}",
                repo=repo_name,
                commit=after_sha
            )

            return {
                "status": "COMPLETED" if is_valid else "FAILED",
                "validation_status": val_status,
                "commit_sha": after_sha,
                "api_changes_count": len(created_changes),
                "published": should_publish,
                "overall_summary": ai_plan.overall_summary,
            }

        except Exception as e:
            logger.error(f"Pipeline failure on {repo_name} @ {after_sha[:7]}: {str(e)}", exc_info=True)
            existing_commit.status = "FAILED"
            existing_commit.error_message = str(e)
            repository.status = "FAILED"
            db.commit()
            raise
