"""OpenAPI validation and deterministic auto-repair."""

import re
from typing import Any, Dict, List, Tuple
from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

from app.core.logging import logger


class OpenAPIValidator:
    """Validates OpenAPI 3.0 / 3.1 specifications and applies deterministic repairs."""

    @classmethod
    def validate_spec(cls, spec: Dict[str, Any]) -> Tuple[bool, List[str], str]:
        """Validate an OpenAPI specification dictionary. Returns (is_valid, errors, status)."""
        try:
            validate(spec)
            return True, [], "VALID"
        except OpenAPIValidationError as e:
            logger.warning(f"OpenAPI validation error: {str(e)}")
            errors = [str(e)]

            # Attempt deterministic repair
            repaired_spec, repaired = cls.repair_spec(spec)
            if repaired:
                try:
                    validate(repaired_spec)
                    logger.info("OpenAPI specification repaired successfully.")
                    return True, [], "REPAIRED"
                except Exception as e2:
                    errors.append(f"Repair attempt failed: {str(e2)}")

            return False, errors, "INVALID"
        except Exception as e:
            logger.warning(f"Unexpected validation error: {str(e)}")
            return False, [str(e)], "INVALID"

    @classmethod
    def repair_spec(cls, spec: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Apply deterministic structural repairs for missing required OpenAPI elements."""
        repaired = False
        repaired_spec = dict(spec)

        # 1. Ensure openapi version
        if "openapi" not in repaired_spec:
            repaired_spec["openapi"] = "3.0.3"
            repaired = True

        # 2. Ensure info object
        info = repaired_spec.setdefault("info", {})
        if "title" not in info:
            info["title"] = "API Documentation"
            repaired = True
        if "version" not in info:
            info["version"] = "1.0.0"
            repaired = True

        # 3. Ensure paths object
        paths = repaired_spec.setdefault("paths", {})

        # 4. Check all operations for responses and path parameters
        for path_str, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            path_param_names = set(re.findall(r"\{([a-zA-Z0-9_]+)(?::[a-zA-Z0-9_]+)?\}", path_str))

            for method, operation in path_item.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch", "options", "head"):
                    continue
                if not isinstance(operation, dict):
                    continue

                # Ensure responses exists
                responses = operation.setdefault("responses", {})
                if not responses:
                    responses["200"] = {"description": "Successful Response"}
                    repaired = True
                else:
                    for status_code, resp_obj in responses.items():
                        if isinstance(resp_obj, dict) and "description" not in resp_obj:
                            resp_obj["description"] = "Response"
                            repaired = True

                # Ensure path parameters defined in path_str exist in parameters
                params = operation.setdefault("parameters", [])
                existing_param_names = {p.get("name") for p in params if isinstance(p, dict) and p.get("in") == "path"}

                for missing_param in path_param_names - existing_param_names:
                    params.append({
                        "name": missing_param,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": f"Parameter {missing_param}",
                    })
                    repaired = True

        return repaired_spec, repaired
