"""SQLAlchemy model for Documentation Versions."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class DocumentationVersion(Base):
    __tablename__ = "documentation_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="SET NULL"), nullable=True, index=True)

    version = Column(Integer, nullable=False, default=1)
    openapi_json = Column(JSON, nullable=False)
    validation_status = Column(String(50), nullable=False, default="VALID")  # VALID, INVALID, REPAIRED
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="documentation_versions")
    commit = relationship("Commit", back_populates="documentation_versions")

    def __repr__(self) -> str:
        return f"<DocumentationVersion(id={self.id}, repo_id={self.repository_id}, v={self.version}, status='{self.validation_status}')>"
