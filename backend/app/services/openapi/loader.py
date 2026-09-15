"""OpenAPI loader, parser, and baseline specification generator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.core.logging import logger
from app.services.analyzers.base import APISnapshot, SchemaSnapshot


class OpenAPILoader:
    """Loads existing OpenAPI documents or generates baseline specifications from AST snapshots."""

    STANDARD_FILENAMES = [
        "openapi.json",
        "openapi.yaml",
        "openapi.yml",
        "swagger.json",
        "swagger.yaml",
        "swagger.yml",
        "docs/openapi.json",
        "docs/openapi.yaml",
    ]

    @classmethod
    def find_and_load(cls, repo_path: Path | str, custom_path: str = "") -> Optional[Dict[str, Any]]:
        """Search repository for OpenAPI specification file and load as dict."""
        base = Path(repo_path).resolve()

        # Check custom path first if provided
        if custom_path:
            p = base / custom_path
            if p.is_file():
                return cls._load_file(p)

        # Check standard file locations
        for rel_name in cls.STANDARD_FILENAMES:
            p = base / rel_name
            if p.is_file():
                logger.info(f"Discovered existing OpenAPI spec at {rel_name}")
                return cls._load_file(p)

        return None

    @classmethod
    def _load_file(cls, path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON or YAML file."""
        try:
            content = path.read_text(encoding="utf-8")
            if path.suffix.lower() in (".yaml", ".yml"):
                return yaml.safe_load(content)
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to parse OpenAPI file {path}: {str(e)}")
            return None

    @classmethod
    def generate_baseline(
        cls,
        snapshot: APISnapshot,
        title: str = "Backend API Documentation",
        version: str = "1.0.0",
        description: str = "Auto-generated OpenAPI specification from source code."
    ) -> Dict[str, Any]:
        """Generate a complete, standard-compliant OpenAPI 3.0.3 document from an APISnapshot."""
        openapi_doc: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
                "description": description,
            },
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                },
            },
        }

        # 1. Register Pydantic schemas in components.schemas
        for schema_name, schema in snapshot.schemas.items():
            openapi_doc["components"]["schemas"][schema_name] = cls._convert_schema_to_openapi(schema)

        # 2. Register Endpoints
        for _, ep in snapshot.endpoints.items():
            path_item = openapi_doc["paths"].setdefault(ep.path, {})
            method_key = ep.method.lower()

            operation: Dict[str, Any] = {
                "summary": ep.summary or f"{ep.method.upper()} {ep.path}",
                "description": ep.description or "",
                "operationId": f"{ep.function_name}_{ep.method.lower()}",
                "parameters": [],
                "responses": {},
            }

            if ep.tags:
                operation["tags"] = ep.tags

            # Convert Parameters
            for p in ep.parameters:
                operation["parameters"].append({
                    "name": p.name,
                    "in": p.location,
                    "required": p.required,
                    "schema": {"type": p.type},
                    "description": p.description or "",
                })

            # Convert Request Body
            if ep.request_body:
                schema_name = ep.request_body.name
                if schema_name not in openapi_doc["components"]["schemas"]:
                    openapi_doc["components"]["schemas"][schema_name] = cls._convert_schema_to_openapi(ep.request_body)

                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                }

            # Convert Response Body
            status_str = str(ep.status_code)
            if ep.response_body:
                schema_name = ep.response_body.name
                if schema_name not in openapi_doc["components"]["schemas"]:
                    openapi_doc["components"]["schemas"][schema_name] = cls._convert_schema_to_openapi(ep.response_body)

                operation["responses"][status_str] = {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                }
            else:
                operation["responses"][status_str] = {
                    "description": "Successful Response"
                }

            # Security requirement
            if ep.auth_required:
                operation["security"] = [{"BearerAuth": []}]

            path_item[method_key] = operation

        return openapi_doc

    @classmethod
    def _convert_schema_to_openapi(cls, schema: SchemaSnapshot) -> Dict[str, Any]:
        """Convert AST SchemaSnapshot to OpenAPI JSON Schema."""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for f in schema.fields:
            prop_def: Dict[str, Any] = {"type": f.type}
            if f.description:
                prop_def["description"] = f.description
            if f.default is not None:
                prop_def["default"] = f.default

            properties[f.name] = prop_def
            if f.required:
                required.append(f.name)

        res: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            res["required"] = required

        return res
