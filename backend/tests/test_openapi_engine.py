"""Tests for OpenAPI Engine: Loader, Baseline Generator, Updater, Validator, and Publisher."""

from app.services.analyzers.base import (
    APIEndpointSnapshot,
    APISnapshot,
    FieldSnapshot,
    ParameterSnapshot,
    SchemaSnapshot,
)
from app.services.openapi.loader import OpenAPILoader
from app.services.openapi.updater import OpenAPIUpdater
from app.services.openapi.validator import OpenAPIValidator
from app.schemas.agent import (
    DocumentationChanges,
    FieldChange,
    ImpactAnalysis,
    SingleAPIChangePlan,
)


def test_baseline_generation_and_validation():
    """Test generating baseline OpenAPI spec from AST snapshot and validating it."""
    snapshot = APISnapshot()
    user_schema = SchemaSnapshot(
        name="User",
        fields=[
            FieldSnapshot(name="id", type="integer", required=True),
            FieldSnapshot(name="username", type="string", required=True),
        ],
    )
    snapshot.schemas["User"] = user_schema

    snapshot.add_endpoint(
        APIEndpointSnapshot(
            method="GET",
            path="/users",
            function_name="get_users",
            summary="List users",
            response_body=user_schema,
        )
    )

    spec = OpenAPILoader.generate_baseline(snapshot, title="Test API", version="1.0.0")

    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "Test API"
    assert "/users" in spec["paths"]
    assert "get" in spec["paths"]["/users"]
    assert "User" in spec["components"]["schemas"]

    # Validate spec
    is_valid, errors, status = OpenAPIValidator.validate_spec(spec)
    assert is_valid is True
    assert status == "VALID"


def test_updater_applies_add_and_remove():
    """Test adding and removing endpoints deterministically."""
    base_spec = {
        "openapi": "3.0.3",
        "info": {"title": "Sample API", "version": "1.0.0"},
        "paths": {
            "/existing": {
                "get": {
                    "summary": "Existing endpoint",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "components": {"schemas": {}},
    }

    # 1. Add POST /items
    add_plan = SingleAPIChangePlan(
        type="added",
        method="POST",
        path="/items",
        summary="Create Item",
        explanation="Added new items creation endpoint",
        documentation_changes=DocumentationChanges(
            request_fields_added=[
                FieldChange(name="title", type="string", required=True),
                FieldChange(name="price", type="number", required=False),
            ]
        ),
        impact=ImpactAnalysis(severity="LOW", reason="Non-breaking additive change"),
        confidence=0.98,
    )

    updated_spec = OpenAPIUpdater.apply_change_plan(base_spec, [add_plan])
    assert "/items" in updated_spec["paths"]
    assert "post" in updated_spec["paths"]["/items"]
    assert "/existing" in updated_spec["paths"]  # Unrelated path preserved!

    # 2. Remove GET /existing
    remove_plan = SingleAPIChangePlan(
        type="removed",
        method="GET",
        path="/existing",
        summary="Delete existing",
        explanation="Endpoint deprecated and deleted",
        impact=ImpactAnalysis(severity="HIGH", reason="Breaking removal"),
        confidence=0.99,
    )

    final_spec = OpenAPIUpdater.apply_change_plan(updated_spec, [remove_plan])
    assert "/existing" not in final_spec["paths"]
    assert "/items" in final_spec["paths"]


def test_updater_modifies_request_fields_preserving_others():
    """Test modifying an endpoint's request fields without altering unrelated endpoints."""
    base_spec = {
        "openapi": "3.0.3",
        "info": {"title": "Sample API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "summary": "Create User",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserCreate"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/products": {
                "get": {
                    "summary": "List Products",
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {
            "schemas": {
                "UserCreate": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            }
        },
    }

    modify_plan = SingleAPIChangePlan(
        type="modified",
        method="POST",
        path="/users",
        summary="Create User with Email",
        explanation="Email field is now mandatory",
        documentation_changes=DocumentationChanges(
            request_fields_added=[
                FieldChange(name="email", type="string", required=True, description="User email address")
            ]
        ),
        impact=ImpactAnalysis(severity="HIGH", reason="Added required request field"),
        confidence=0.96,
    )

    updated = OpenAPIUpdater.apply_change_plan(base_spec, [modify_plan])

    # Check that UserCreate schema was updated
    user_schema = updated["components"]["schemas"]["UserCreate"]
    assert "email" in user_schema["properties"]
    assert "name" in user_schema["properties"]
    assert "email" in user_schema["required"]
    assert "name" in user_schema["required"]

    # Check that /products was NOT touched
    assert updated["paths"]["/products"]["get"]["summary"] == "List Products"

    # Validate updated spec
    is_valid, errors, status = OpenAPIValidator.validate_spec(updated)
    assert is_valid is True
