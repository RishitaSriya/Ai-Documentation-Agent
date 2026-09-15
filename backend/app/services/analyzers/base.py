"""Abstract Base Class for API Analyzers and Snapshot data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ParameterSnapshot:
    name: str
    location: str  # path, query, header, cookie
    type: str = "string"
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FieldSnapshot:
    name: str
    type: str = "string"
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchemaSnapshot:
    name: str
    fields: List[FieldSnapshot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields]
        }


@dataclass
class APIEndpointSnapshot:
    method: str  # GET, POST, PUT, DELETE, PATCH, etc.
    path: str    # e.g., /users/{user_id}
    function_name: str
    summary: Optional[str] = None
    description: Optional[str] = None
    status_code: int = 200
    parameters: List[ParameterSnapshot] = field(default_factory=list)
    request_body: Optional[SchemaSnapshot] = None
    response_body: Optional[SchemaSnapshot] = None
    auth_required: bool = False
    auth_dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_file: str = ""
    source_line: int = 1

    @property
    def key(self) -> str:
        """Unique identifier key for the endpoint method + path."""
        return f"{self.method.upper()}:{self.path}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.upper(),
            "path": self.path,
            "function_name": self.function_name,
            "summary": self.summary,
            "description": self.description,
            "status_code": self.status_code,
            "parameters": [p.to_dict() for p in self.parameters],
            "request_body": self.request_body.to_dict() if self.request_body else None,
            "response_body": self.response_body.to_dict() if self.response_body else None,
            "auth_required": self.auth_required,
            "auth_dependencies": self.auth_dependencies,
            "tags": self.tags,
            "source_file": self.source_file,
            "source_line": self.source_line,
        }


@dataclass
class APISnapshot:
    framework: str = "fastapi"
    commit_sha: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    endpoints: Dict[str, APIEndpointSnapshot] = field(default_factory=dict)
    schemas: Dict[str, SchemaSnapshot] = field(default_factory=dict)

    def add_endpoint(self, endpoint: APIEndpointSnapshot) -> None:
        self.endpoints[endpoint.key] = endpoint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "commit_sha": self.commit_sha,
            "timestamp": self.timestamp.isoformat(),
            "endpoints": {k: ep.to_dict() for k, ep in self.endpoints.items()},
            "schemas": {k: sc.to_dict() for k, sc in self.schemas.items()},
        }


class APIAnalyzer(ABC):
    """Abstract base analyzer for backend repositories."""

    @abstractmethod
    def analyze(
        self,
        repository_path: Path | str,
        target_files: Optional[List[str]] = None,
        commit_sha: Optional[str] = None
    ) -> APISnapshot:
        """Analyze source code and return an APISnapshot."""
        pass
