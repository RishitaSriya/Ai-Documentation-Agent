"""Tests for FastAPI AST Analyzer."""

from pathlib import Path
from app.services.analyzers.fastapi_analyzer import FastAPIAnalyzer


def test_fastapi_analyzer_extracts_endpoints_and_models(tmp_path):
    """Test AST analysis of sample FastAPI source files."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Create schemas/user.py
    schemas_dir = app_dir / "schemas"
    schemas_dir.mkdir()
    user_schema_file = schemas_dir / "user.py"
    user_schema_file.write_text(
        """from pydantic import BaseModel, Field
from typing import Optional

class UserCreate(BaseModel):
    name: str = Field(..., description="User full name")
    email: str
    is_admin: bool = False
    bio: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
""",
        encoding="utf-8",
    )

    # Create routes/users.py
    routes_dir = app_dir / "routes"
    routes_dir.mkdir()
    users_route_file = routes_dir / "users.py"
    users_route_file.write_text(
        """from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

def get_current_user(token: str = Header(...)):
    return {"token": token}

@router.get("", response_model=UserResponse, summary="List all users")
def list_users(limit: int = 20, offset: int = 0):
    \"\"\"Fetch paginated list of users.\"\"\"
    return []

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, auth: dict = Depends(get_current_user)):
    \"\"\"Create a new user account.\"\"\"
    return user

@router.get("/{user_id}")
def get_user_by_id(user_id: int, include_posts: bool = False):
    \"\"\"Get single user by primary ID.\"\"\"
    return {"user_id": user_id}

@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int):
    return None
""",
        encoding="utf-8",
    )

    analyzer = FastAPIAnalyzer()
    snapshot = analyzer.analyze(tmp_path)

    assert snapshot.framework == "fastapi"
    assert len(snapshot.schemas) >= 2
    assert "UserCreate" in snapshot.schemas
    assert "UserResponse" in snapshot.schemas

    # Check UserCreate fields
    user_create_fields = {f.name: f for f in snapshot.schemas["UserCreate"].fields}
    assert user_create_fields["name"].required is True
    assert user_create_fields["name"].type == "string"
    assert user_create_fields["email"].required is True
    assert user_create_fields["is_admin"].required is False
    assert user_create_fields["bio"].required is False

    # Check Endpoints
    assert len(snapshot.endpoints) == 4

    # 1. GET /users
    get_users_ep = snapshot.endpoints.get("GET:/users")
    assert get_users_ep is not None
    assert get_users_ep.summary == "List all users"
    assert get_users_ep.tags == ["Users"]
    assert len(get_users_ep.parameters) == 2
    param_names = [p.name for p in get_users_ep.parameters]
    assert "limit" in param_names
    assert "offset" in param_names

    # 2. POST /users
    post_user_ep = snapshot.endpoints.get("POST:/users")
    assert post_user_ep is not None
    assert post_user_ep.status_code == 201
    assert post_user_ep.request_body is not None
    assert post_user_ep.request_body.name == "UserCreate"
    assert post_user_ep.auth_required is True
    assert "get_current_user" in post_user_ep.auth_dependencies

    # 3. GET /users/{user_id}
    get_single_ep = snapshot.endpoints.get("GET:/users/{user_id}")
    assert get_single_ep is not None
    path_param = [p for p in get_single_ep.parameters if p.location == "path"][0]
    assert path_param.name == "user_id"
    assert path_param.type == "integer"
    assert path_param.required is True
    query_param = [p for p in get_single_ep.parameters if p.location == "query"][0]
    assert query_param.name == "include_posts"
    assert query_param.type == "boolean"
    assert query_param.required is False

    # 4. DELETE /users/{user_id}
    del_ep = snapshot.endpoints.get("DELETE:/users/{user_id}")
    assert del_ep is not None
    assert del_ep.status_code == 204
