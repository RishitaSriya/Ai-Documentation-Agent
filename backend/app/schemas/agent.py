"""Pydantic schemas for AI Agent reasoning and change plans."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FieldChange(BaseModel):
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field data type")
    required: bool = Field(default=False, description="Whether the field is required")
    description: Optional[str] = None


class DocumentationChanges(BaseModel):
    request_fields_added: List[FieldChange] = Field(default_factory=list)
    request_fields_removed: List[FieldChange] = Field(default_factory=list)
    response_fields_added: List[FieldChange] = Field(default_factory=list)
    response_fields_removed: List[FieldChange] = Field(default_factory=list)
    path_parameters_added: List[FieldChange] = Field(default_factory=list)
    path_parameters_removed: List[FieldChange] = Field(default_factory=list)
    query_parameters_added: List[FieldChange] = Field(default_factory=list)
    query_parameters_removed: List[FieldChange] = Field(default_factory=list)


class ImpactAnalysis(BaseModel):
    severity: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH")
    reason: str = Field(..., description="Explanation of breaking or non-breaking impact")


class SingleAPIChangePlan(BaseModel):
    type: str = Field(..., description="added, removed, or modified")
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Endpoint path")
    summary: Optional[str] = Field(default=None, description="Concise summary for OpenAPI operation")
    description: Optional[str] = Field(default=None, description="Detailed description for OpenAPI operation")
    documentation_changes: DocumentationChanges = Field(default_factory=DocumentationChanges)
    explanation: str = Field(..., description="AI explanation of the API change")
    impact: ImpactAnalysis
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")


class APIChangePlan(BaseModel):
    changes: List[SingleAPIChangePlan] = Field(default_factory=list)
    overall_summary: Optional[str] = None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    commit_id: Optional[int] = None
    model: str
    status: str
    error: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    created_at: datetime
