"""Deterministic comparator between API snapshots."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set

from app.services.analyzers.base import (
    APIEndpointSnapshot,
    APISnapshot,
    FieldSnapshot,
    ParameterSnapshot,
    SchemaSnapshot,
)


@dataclass
class DetectedAPIChange:
    change_type: str  # added, removed, modified
    method: str
    path: str
    summary: Optional[str] = None
    old_structure: Optional[Dict[str, Any]] = None
    new_structure: Optional[Dict[str, Any]] = None
    diff_details: Dict[str, Any] = field(default_factory=dict)
    default_severity: str = "LOW"  # LOW, MEDIUM, HIGH
    source_file: Optional[str] = None
    source_line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class APIComparator:
    """Compares two APISnapshots to detect added, removed, and modified endpoints."""

    @classmethod
    def compare(
        cls,
        prev_snapshot: Optional[APISnapshot],
        curr_snapshot: APISnapshot
    ) -> List[DetectedAPIChange]:
        """Produce a list of detected API changes between snapshots."""
        changes: List[DetectedAPIChange] = []

        if prev_snapshot is None:
            # All current endpoints are 'added'
            for key, ep in curr_snapshot.endpoints.items():
                changes.append(
                    DetectedAPIChange(
                        change_type="added",
                        method=ep.method,
                        path=ep.path,
                        summary=ep.summary,
                        old_structure=None,
                        new_structure=ep.to_dict(),
                        diff_details={"reason": "Initial or newly introduced endpoint"},
                        default_severity="LOW",
                        source_file=ep.source_file,
                        source_line=ep.source_line,
                    )
                )
            return changes

        prev_keys: Set[str] = set(prev_snapshot.endpoints.keys())
        curr_keys: Set[str] = set(curr_snapshot.endpoints.keys())

        # 1. Added Endpoints
        added_keys = curr_keys - prev_keys
        for key in sorted(added_keys):
            ep = curr_snapshot.endpoints[key]
            changes.append(
                DetectedAPIChange(
                    change_type="added",
                    method=ep.method,
                    path=ep.path,
                    summary=ep.summary,
                    old_structure=None,
                    new_structure=ep.to_dict(),
                    diff_details={"reason": "New endpoint created"},
                    default_severity="LOW",
                    source_file=ep.source_file,
                    source_line=ep.source_line,
                )
            )

        # 2. Removed Endpoints
        removed_keys = prev_keys - curr_keys
        for key in sorted(removed_keys):
            ep = prev_snapshot.endpoints[key]
            changes.append(
                DetectedAPIChange(
                    change_type="removed",
                    method=ep.method,
                    path=ep.path,
                    summary=ep.summary,
                    old_structure=ep.to_dict(),
                    new_structure=None,
                    diff_details={"reason": "Endpoint deleted or removed from routes"},
                    default_severity="HIGH",
                    source_file=ep.source_file,
                    source_line=ep.source_line,
                )
            )

        # 3. Common Endpoints -> Check for structural modifications
        common_keys = prev_keys & curr_keys
        for key in sorted(common_keys):
            prev_ep = prev_snapshot.endpoints[key]
            curr_ep = curr_snapshot.endpoints[key]

            diff_details, severity = cls._diff_endpoint(prev_ep, curr_ep)
            if diff_details:
                changes.append(
                    DetectedAPIChange(
                        change_type="modified",
                        method=curr_ep.method,
                        path=curr_ep.path,
                        summary=curr_ep.summary or prev_ep.summary,
                        old_structure=prev_ep.to_dict(),
                        new_structure=curr_ep.to_dict(),
                        diff_details=diff_details,
                        default_severity=severity,
                        source_file=curr_ep.source_file,
                        source_line=curr_ep.source_line,
                    )
                )

        return changes

    @classmethod
    def _diff_endpoint(
        cls,
        prev_ep: APIEndpointSnapshot,
        curr_ep: APIEndpointSnapshot
    ) -> Tuple[Dict[str, Any], str]:
        """Deep comparison between two endpoints for schema/parameter changes."""
        diffs: Dict[str, Any] = {}
        max_severity = "LOW"

        def escalate(sev: str):
            nonlocal max_severity
            rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
            if rank.get(sev, 1) > rank.get(max_severity, 1):
                max_severity = sev

        # Check Parameters (path, query, header)
        prev_params = {p.name: p for p in prev_ep.parameters}
        curr_params = {p.name: p for p in curr_ep.parameters}

        added_params = []
        for name, p in curr_params.items():
            if name not in prev_params:
                added_params.append(p.to_dict())
                escalate("HIGH" if p.required else "MEDIUM")
            elif prev_params[name].type != p.type or prev_params[name].required != p.required:
                diffs.setdefault("parameters_modified", []).append({
                    "name": name,
                    "old": prev_params[name].to_dict(),
                    "new": p.to_dict(),
                })
                if p.required and not prev_params[name].required:
                    escalate("HIGH")

        removed_params = []
        for name, p in prev_params.items():
            if name not in curr_params:
                removed_params.append(p.to_dict())
                escalate("HIGH" if p.location == "path" or p.required else "MEDIUM")

        if added_params:
            diffs["parameters_added"] = added_params
        if removed_params:
            diffs["parameters_removed"] = removed_params

        # Check Request Body Schema
        req_diffs, req_sev = cls._diff_schema(prev_ep.request_body, curr_ep.request_body, "request")
        if req_diffs:
            diffs["request_body_diff"] = req_diffs
            escalate(req_sev)

        # Check Response Body Schema
        resp_diffs, resp_sev = cls._diff_schema(prev_ep.response_body, curr_ep.response_body, "response")
        if resp_diffs:
            diffs["response_body_diff"] = resp_diffs
            escalate(resp_sev)

        # Check Auth changes
        if prev_ep.auth_required != curr_ep.auth_required or set(prev_ep.auth_dependencies) != set(curr_ep.auth_dependencies):
            diffs["auth_changed"] = {
                "old_required": prev_ep.auth_required,
                "new_required": curr_ep.auth_required,
                "old_deps": prev_ep.auth_dependencies,
                "new_deps": curr_ep.auth_dependencies,
            }
            escalate("HIGH" if curr_ep.auth_required and not prev_ep.auth_required else "MEDIUM")

        # Check Status Code change
        if prev_ep.status_code != curr_ep.status_code:
            diffs["status_code_changed"] = {
                "old": prev_ep.status_code,
                "new": curr_ep.status_code,
            }
            escalate("MEDIUM")

        # Check Summary / Description change
        if prev_ep.summary != curr_ep.summary or prev_ep.description != curr_ep.description:
            diffs["docstring_changed"] = {
                "old_summary": prev_ep.summary,
                "new_summary": curr_ep.summary,
            }

        return diffs, max_severity

    @classmethod
    def _diff_schema(
        cls,
        prev_schema: Optional[SchemaSnapshot],
        curr_schema: Optional[SchemaSnapshot],
        context: str = "request"
    ) -> Tuple[Dict[str, Any], str]:
        """Compare two Pydantic schemas field by field."""
        if prev_schema is None and curr_schema is None:
            return {}, "LOW"
        if prev_schema is None and curr_schema is not None:
            return {"schema_added": curr_schema.to_dict()}, "HIGH" if context == "request" else "LOW"
        if prev_schema is not None and curr_schema is None:
            return {"schema_removed": prev_schema.to_dict()}, "HIGH"

        diffs: Dict[str, Any] = {}
        severity = "LOW"

        prev_fields = {f.name: f for f in prev_schema.fields}
        curr_fields = {f.name: f for f in curr_schema.fields}

        added_fields = []
        for name, f in curr_fields.items():
            if name not in prev_fields:
                added_fields.append(f.to_dict())
                if context == "request":
                    severity = "HIGH" if f.required else "MEDIUM"
                else:
                    severity = "LOW"
            elif prev_fields[name].type != f.type or prev_fields[name].required != f.required:
                diffs.setdefault("fields_modified", []).append({
                    "name": name,
                    "old": prev_fields[name].to_dict(),
                    "new": f.to_dict(),
                })
                if context == "request" and f.required and not prev_fields[name].required:
                    severity = "HIGH"

        removed_fields = []
        for name, f in prev_fields.items():
            if name not in curr_fields:
                removed_fields.append(f.to_dict())
                severity = "HIGH"  # Removing response field or request field is breaking

        if added_fields:
            diffs["fields_added"] = added_fields
        if removed_fields:
            diffs["fields_removed"] = removed_fields

        return diffs, severity
