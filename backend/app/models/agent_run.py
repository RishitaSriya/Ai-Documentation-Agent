"""SQLAlchemy model for Agent Runs."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="SET NULL"), nullable=True, index=True)

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    model = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="SUCCESS")  # SUCCESS, RETRIED, FAILED
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="agent_runs")
    commit = relationship("Commit", back_populates="agent_runs")

    def __repr__(self) -> str:
        return f"<AgentRun(id={self.id}, model='{self.model}', status='{self.status}')>"
