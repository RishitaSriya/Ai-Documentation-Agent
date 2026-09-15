"""SQLAlchemy model for GitHub Repositories."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    github_repo_id = Column(String(100), nullable=True, index=True)
    owner = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    default_branch = Column(String(100), nullable=False, default="main")
    clone_url = Column(String(255), nullable=False)
    webhook_id = Column(String(100), nullable=True)

    # Repository Analysis Configuration
    framework = Column(String(50), nullable=False, default="fastapi")
    source_root = Column(String(255), nullable=False, default="")
    openapi_path = Column(String(255), nullable=False, default="")
    auto_publish = Column(Boolean, nullable=False, default=True)
    confidence_threshold = Column(Float, nullable=False, default=0.85)

    # State & Audit
    status = Column(String(50), nullable=False, default="IDLE")  # IDLE, PROCESSING, SYNCED, FAILED
    last_processed_commit = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan", order_by="desc(Commit.created_at)")
    api_changes = relationship("APIChange", back_populates="repository", cascade="all, delete-orphan", order_by="desc(APIChange.created_at)")
    documentation_versions = relationship("DocumentationVersion", back_populates="repository", cascade="all, delete-orphan", order_by="desc(DocumentationVersion.version)")
    agent_runs = relationship("AgentRun", back_populates="repository", cascade="all, delete-orphan", order_by="desc(AgentRun.created_at)")

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, full_name='{self.full_name}', branch='{self.default_branch}')>"
