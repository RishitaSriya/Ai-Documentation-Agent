"""Deterministic OpenAPI Specification Update Engine."""

import copy
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.schemas.agent import FieldChange, SingleAPIChangePlan


class OpenAPIUpdater:
    """Applies structured change plans deterministically to an OpenAPI document."""

    @classmethod
    def apply_change_plan(
        cls,
        base_openapi: Dict[str, Any],
        change_plan: List[SingleAPIChangePlan]
    ) -> Dict[str, Any]:
        """Apply a list of change plans to the OpenAPI specification dictionary without touching unrelated paths."""
        # Deep copy to ensure original spec remains unmodified until validated
        updated_spec = copy.deepcopy(base_openapi)
        updated_spec.setdefault("paths", {})
        updated_spec.setdefault("components", {}).setdefault("schemas", {})

        for change in change_plan:
            change_type = change.type.lower()
            method = change.method.lower()
            path = change.path

            logger.info(f"Applying OpenAPI update: [{change_type.upper()}] {method.upper()} {path}")

            if change_type == "added":
                cls._apply_add_endpoint(updated_spec, change)
            elif change_type == "removed":
                cls._apply_remove_endpoint(updated_spec, path, method)
            elif change_type == "modified":
                cls._apply_modify_endpoint(updated_spec, change)

        return updated_spec

    @classmethod
    def _apply_add_endpoint(cls, spec: Dict[str, Any], change: SingleAPIChangePlan) -> None:
        """Add a new endpoint operation to the spec."""
        path_item = spec["paths"].setdefault(change.path, {})
        method_key = change.method.lower()

        operation = {
            "summary": change.summary or f"{change.method.upper()} {change.path}",
            "description": change.description or change.explanation or "",
            "operationId": f"{change.method.lower()}_{change.path.replace('/', '_').strip('_')}",
            "parameters": [],
            "responses": {
                "200": {"description": "Successful Response"}
            },
        }

        # Apply Path and Query Parameters from doc changes
        doc_ch = change.documentation_changes
        for p in doc_ch.path_parameters_added:
            operation["parameters"].append({
                "name": p.name,
                "in": "path",
                "required": True,
                "schema": {"type": p.type},
                "description": p.description or "",
            })

        for q in doc_ch.query_parameters_added:
            operation["parameters"].append({
                "name": q.name,
                "in": "query",
                "required": q.required,
                "schema": {"type": q.type},
                "description": q.description or "",
            })

        # Apply Request Body
        if doc_ch.request_fields_added:
            schema_name = f"{change.method.capitalize()}{change.path.replace('/', ' ').title().replace(' ', '')}Request"
            schema_props = {}
            required_props = []

            for rf in doc_ch.request_fields_added:
                schema_props[rf.name] = {"type": rf.type}
                if rf.description:
                    schema_props[rf.name]["description"] = rf.description
                if rf.required:
                    required_props.append(rf.name)

            spec["components"]["schemas"][schema_name] = {
                "type": "object",
                "properties": schema_props,
                "required": required_props,
            }

            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                    }
                },
            }

        path_item[method_key] = operation

    @classmethod
    def _apply_remove_endpoint(cls, spec: Dict[str, Any], path: str, method: str) -> None:
        """Remove an endpoint operation from paths."""
        if path in spec["paths"]:
            if method in spec["paths"][path]:
                del spec["paths"][path][method]
                logger.info(f"Removed operation {method.upper()} from {path}")

            # If no methods remain in path, remove the path entry
            if not spec["paths"][path]:
                del spec["paths"][path]
                logger.info(f"Removed empty path entry {path}")

    @classmethod
    def _apply_modify_endpoint(cls, spec: Dict[str, Any], change: SingleAPIChangePlan) -> None:
        """Modify an existing endpoint operation."""
        path_item = spec["paths"].setdefault(change.path, {})
        method_key = change.method.lower()

        operation = path_item.setdefault(method_key, {
            "summary": change.summary or f"{change.method.upper()} {change.path}",
            "description": "",
            "parameters": [],
            "responses": {"200": {"description": "Successful Response"}}
        })

        # Update summary and description if provided
        if change.summary:
            operation["summary"] = change.summary
        if change.description:
            operation["description"] = change.description

        doc_ch = change.documentation_changes

        # 1. Update Request Body Schema
        if doc_ch.request_fields_added or doc_ch.request_fields_removed:
            cls._update_request_body_schema(spec, operation, change)

        # 2. Update Path/Query Parameters
        cls._update_parameters(operation, doc_ch)

    @classmethod
    def _update_request_body_schema(
        cls,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
        change: SingleAPIChangePlan
    ) -> None:
        """Update requestBody schema in components."""
        doc_ch = change.documentation_changes

        # Identify target schema name
        ref_path = ""
        if "requestBody" in operation:
            schema_obj = operation["requestBody"].get("content", {}).get("application/json", {}).get("schema", {})
            ref_path = schema_obj.get("$ref", "")

        schema_name = ""
        if ref_path.startswith("#/components/schemas/"):
            schema_name = ref_path.replace("#/components/schemas/", "")

        if not schema_name:
            schema_name = f"{change.method.capitalize()}{change.path.replace('/', ' ').title().replace(' ', '')}Request"
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                    }
                }
            }

        target_schema = spec["components"]["schemas"].setdefault(schema_name, {
            "type": "object",
            "properties": {},
            "required": [],
        })
        target_schema.setdefault("properties", {})
        target_schema.setdefault("required", [])

        # Add / update fields
        for f in doc_ch.request_fields_added:
            target_schema["properties"][f.name] = {"type": f.type}
            if f.description:
                target_schema["properties"][f.name]["description"] = f.description
            if f.required and f.name not in target_schema["required"]:
                target_schema["required"].append(f.name)
            elif not f.required and f.name in target_schema["required"]:
                target_schema["required"].remove(f.name)

        # Remove fields
        for f in doc_ch.request_fields_removed:
            if f.name in target_schema["properties"]:
                del target_schema["properties"][f.name]
            if f.name in target_schema["required"]:
                target_schema["required"].remove(f.name)

    @classmethod
    def _update_parameters(cls, operation: Dict[str, Any], doc_ch: Any) -> None:
        """Add / update / remove parameters."""
        params = operation.setdefault("parameters", [])

        # Process additions
        for p in doc_ch.path_parameters_added:
            # Replace existing or append
            params[:] = [param for param in params if not (param.get("name") == p.name and param.get("in") == "path")]
            params.append({
                "name": p.name,
                "in": "path",
                "required": True,
                "schema": {"type": p.type},
                "description": p.description or "",
            })

        for q in doc_ch.query_parameters_added:
            params[:] = [param for param in params if not (param.get("name") == q.name and param.get("in") == "query")]
            params.append({
                "name": q.name,
                "in": "query",
                "required": q.required,
                "schema": {"type": q.type},
                "description": q.description or "",
            })

        # Process removals
        removed_names = {p.name for p in doc_ch.path_parameters_removed + doc_ch.query_parameters_removed}
        if removed_names:
            params[:] = [p for p in params if p.get("name") not in removed_names]
