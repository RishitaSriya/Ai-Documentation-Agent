"""Pydantic schemas for API Changes."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class APIChangeBase(BaseModel):
    change_type: str = Field(..., description="Change type: added, removed, modified")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    path: str = Field(..., description="Endpoint path")
    summary: Optional[str] = None
    old_structure: Optional[Dict[str, Any]] = None
    new_structure: Optional[Dict[str, Any]] = None
    ai_explanation: Optional[str] = None
    impact_analysis: Optional[Dict[str, Any]] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="AUTO_APPLIED")
    source_file: Optional[str] = None
    source_line: Optional[int] = None


class APIChangeCreate(APIChangeBase):
    repository_id: int
    commit_id: Optional[int] = None


class APIChangeResponse(APIChangeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    commit_id: Optional[int] = None
    commit_sha: Optional[str] = None
    created_at: datetime
