"""SQLAlchemy model for Commits."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_sha = Column(String(64), nullable=False, index=True)
    parent_sha = Column(String(64), nullable=True)
    message = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, NO_CHANGES, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="commits")
    api_changes = relationship("APIChange", back_populates="commit", cascade="all, delete-orphan")
    documentation_versions = relationship("DocumentationVersion", back_populates="commit", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="commit", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Commit(id={self.id}, sha='{self.commit_sha[:7]}', status='{self.status}')>"
