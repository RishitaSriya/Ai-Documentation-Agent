"""Database operations for Documentation Versions."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.documentation_version import DocumentationVersion
from app.schemas.documentation import DocumentationVersionCreate


def get_latest_documentation_version(db: Session, repository_id: int) -> Optional[DocumentationVersion]:
    """Retrieve the latest valid documentation version for a repository."""
    return db.query(DocumentationVersion).filter(
        DocumentationVersion.repository_id == repository_id,
        DocumentationVersion.validation_status.in_(["VALID", "REPAIRED"])
    ).order_by(DocumentationVersion.version.desc()).first()


def get_documentation_versions(
    db: Session, repository_id: int, skip: int = 0, limit: int = 50
) -> List[DocumentationVersion]:
    """Retrieve history of documentation versions for a repository."""
    return db.query(DocumentationVersion).filter(
        DocumentationVersion.repository_id == repository_id
    ).order_by(DocumentationVersion.version.desc()).offset(skip).limit(limit).all()


def create_documentation_version(
    db: Session, doc_in: DocumentationVersionCreate
) -> DocumentationVersion:
    """Create and persist a new documentation version."""
    db_doc = DocumentationVersion(
        repository_id=doc_in.repository_id,
        commit_id=doc_in.commit_id,
        version=doc_in.version,
        openapi_json=doc_in.openapi_json,
        validation_status=doc_in.validation_status,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc
