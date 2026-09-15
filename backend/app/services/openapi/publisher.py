"""OpenAPI Publisher and filesystem storage service."""

from pathlib import Path
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger, log_pipeline_event
from app.models.documentation_version import DocumentationVersion
from app.utils.file_utils import write_json_file
from app.db import documentation as doc_db
from app.schemas.documentation import DocumentationVersionCreate


class OpenAPIPublisher:
    """Publishes and versions OpenAPI specifications on disk and in database."""

    @classmethod
    def get_repo_openapi_dir(cls, repo_id: int) -> Path:
        """Get storage path for repository OpenAPI docs."""
        p = settings.openapi_storage_dir / str(repo_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def get_current_openapi(cls, repo_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Retrieve current active OpenAPI specification from DB or disk."""
        latest_version = doc_db.get_latest_documentation_version(db, repo_id)
        if latest_version and isinstance(latest_version.openapi_json, dict):
            return latest_version.openapi_json

        # Fallback to disk
        doc_path = cls.get_repo_openapi_dir(repo_id) / "openapi.json"
        if doc_path.is_file():
            import json
            try:
                return json.loads(doc_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    @classmethod
    def publish_version(
        cls,
        db: Session,
        repo_id: int,
        openapi_spec: Dict[str, Any],
        commit_id: Optional[int] = None,
        validation_status: str = "VALID"
    ) -> DocumentationVersion:
        """Save a new version of the OpenAPI specification."""
        latest = doc_db.get_latest_documentation_version(db, repo_id)
        next_version = (latest.version + 1) if latest else 1

        # 1. Store in Database
        doc_in = DocumentationVersionCreate(
            repository_id=repo_id,
            commit_id=commit_id,
            version=next_version,
            openapi_json=openapi_spec,
            validation_status=validation_status,
        )
        db_doc = doc_db.create_documentation_version(db, doc_in)

        # 2. Write to Disk
        repo_dir = cls.get_repo_openapi_dir(repo_id)
        versioned_file = repo_dir / f"v{next_version}.json"
        current_file = repo_dir / "openapi.json"

        write_json_file(versioned_file, openapi_spec)
        write_json_file(current_file, openapi_spec)

        log_pipeline_event(
            "PUBLISHER",
            f"Published documentation v{next_version} for repository {repo_id} (Status: {validation_status})"
        )
        return db_doc
