"""Pydantic schemas for OpenAPI Documentation versions."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentationVersionBase(BaseModel):
    version: int
    openapi_json: Dict[str, Any]
    validation_status: str = Field(default="VALID")


class DocumentationVersionCreate(DocumentationVersionBase):
    repository_id: int
    commit_id: Optional[int] = None


class DocumentationVersionResponse(DocumentationVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    commit_id: Optional[int] = None
    commit_sha: Optional[str] = None
    created_at: datetime


class DocumentationSummaryResponse(BaseModel):
    repository_id: int
    latest_version: Optional[int] = None
    validation_status: Optional[str] = None
    total_versions: int = 0
    endpoints_count: int = 0
    openapi_url: str
    docs_url: str
