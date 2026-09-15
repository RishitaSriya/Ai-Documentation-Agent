"""SQLAlchemy model for API Changes."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class APIChange(Base):
    __tablename__ = "api_changes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="SET NULL"), nullable=True, index=True)

    # Change classification
    change_type = Column(String(50), nullable=False)  # added, removed, modified
    method = Column(String(20), nullable=False)       # GET, POST, PUT, DELETE, PATCH, etc.
    path = Column(String(500), nullable=False)        # e.g., /users/{user_id}
    summary = Column(String(255), nullable=True)

    # Structural Diffs
    old_structure = Column(JSON, nullable=True)
    new_structure = Column(JSON, nullable=True)

    # AI Reasoning & Analysis
    ai_explanation = Column(Text, nullable=True)
    impact_analysis = Column(JSON, nullable=True)     # {"severity": "HIGH|MEDIUM|LOW", "reason": "..."}
    confidence = Column(Float, nullable=False, default=1.0)
    status = Column(String(50), nullable=False, default="AUTO_APPLIED")  # AUTO_APPLIED, REVIEW_REQUIRED, FAILED

    # Code Traceability
    source_file = Column(String(500), nullable=True)
    source_line = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="api_changes")
    commit = relationship("Commit", back_populates="api_changes")

    def __repr__(self) -> str:
        return f"<APIChange(id={self.id}, type='{self.change_type}', endpoint='{self.method} {self.path}')>"
