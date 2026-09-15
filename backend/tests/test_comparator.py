"""Tests for APIComparator."""

from app.services.analyzers.base import (
    APIEndpointSnapshot,
    APISnapshot,
    FieldSnapshot,
    ParameterSnapshot,
    SchemaSnapshot,
)
from app.services.openapi.comparator import APIComparator


def test_comparator_detects_added_and_removed_endpoints():
    """Test endpoint additions and removals detection."""
    prev_snapshot = APISnapshot()
    prev_snapshot.add_endpoint(
        APIEndpointSnapshot(method="GET", path="/users", function_name="get_users")
    )
    prev_snapshot.add_endpoint(
        APIEndpointSnapshot(method="GET", path="/products", function_name="get_products")
    )

    curr_snapshot = APISnapshot()
    curr_snapshot.add_endpoint(
        APIEndpointSnapshot(method="GET", path="/users", function_name="get_users")
    )
    curr_snapshot.add_endpoint(
        APIEndpointSnapshot(method="POST", path="/users", function_name="create_user")
    )

    changes = APIComparator.compare(prev_snapshot, curr_snapshot)
    assert len(changes) == 2

    change_types = {(c.change_type, c.method, c.path): c for c in changes}
    assert ("added", "POST", "/users") in change_types
    assert ("removed", "GET", "/products") in change_types


def test_comparator_detects_request_field_changes():
    """Test detecting added and removed fields in request body schemas."""
    # Before: UserCreate has only name: str
    prev_user_schema = SchemaSnapshot(
        name="UserCreate",
        fields=[FieldSnapshot(name="name", type="string", required=True)]
    )
    prev_ep = APIEndpointSnapshot(
        method="POST",
        path="/users",
        function_name="create_user",
        request_body=prev_user_schema,
    )
    prev_snapshot = APISnapshot()
    prev_snapshot.add_endpoint(prev_ep)

    # After: UserCreate has name: str, email: str (required), bio: str (optional)
    curr_user_schema = SchemaSnapshot(
        name="UserCreate",
        fields=[
            FieldSnapshot(name="name", type="string", required=True),
            FieldSnapshot(name="email", type="string", required=True),
            FieldSnapshot(name="bio", type="string", required=False),
        ]
    )
    curr_ep = APIEndpointSnapshot(
        method="POST",
        path="/users",
        function_name="create_user",
        request_body=curr_user_schema,
    )
    curr_snapshot = APISnapshot()
    curr_snapshot.add_endpoint(curr_ep)

    changes = APIComparator.compare(prev_snapshot, curr_snapshot)
    assert len(changes) == 1
    mod_change = changes[0]
    assert mod_change.change_type == "modified"
    assert mod_change.default_severity == "HIGH"  # because email is a required request field
    assert "request_body_diff" in mod_change.diff_details
    added_fields = mod_change.diff_details["request_body_diff"]["fields_added"]
    assert len(added_fields) == 2
    added_names = [f["name"] for f in added_fields]
    assert "email" in added_names
    assert "bio" in added_names
