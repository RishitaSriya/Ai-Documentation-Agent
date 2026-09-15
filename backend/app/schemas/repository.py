"""Pydantic schemas for Repository CRUD and responses."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RepositoryBase(BaseModel):
    owner: str = Field(..., description="Repository owner / organization name")
    name: str = Field(..., description="Repository name")
    default_branch: str = Field(default="main", description="Default Git branch name")
    clone_url: Optional[str] = Field(default=None, description="Git clone URL (optional, auto-computed if omitted)")
    framework: str = Field(default="fastapi", description="Detected or configured backend framework")
    source_root: str = Field(default="", description="Path to source root within repository")
    openapi_path: str = Field(default="", description="Relative path to existing OpenAPI file if known")
    auto_publish: bool = Field(default=True, description="Whether to automatically publish high confidence docs")
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Minimum confidence for auto-publish")

    @model_validator(mode="before")
    @classmethod
    def handle_repo_alias(cls, data):
        if isinstance(data, dict):
            data_copy = dict(data)
            if "repo" in data_copy and "name" not in data_copy:
                data_copy["name"] = data_copy["repo"]
            return data_copy
        return data


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryUpdate(BaseModel):
    default_branch: Optional[str] = None
    framework: Optional[str] = None
    source_root: Optional[str] = None
    openapi_path: Optional[str] = None
    auto_publish: Optional[bool] = None
    confidence_threshold: Optional[float] = None
    status: Optional[str] = None


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    github_repo_id: Optional[str] = None
    owner: str
    name: str
    full_name: str
    default_branch: str
    clone_url: str
    webhook_id: Optional[str] = None
    framework: str
    source_root: str
    openapi_path: str
    auto_publish: bool
    confidence_threshold: float
    status: str
    last_processed_commit: Optional[str] = None
    api_changes_count: int = 0
    latest_documentation_version: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class RepositoryDetailResponse(RepositoryResponse):
    recent_commits: List[dict] = []
    recent_changes: List[dict] = []
