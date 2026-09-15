"""User routes."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

USERS_DB = [
    {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "member"},
]


@router.get("", response_model=List[UserResponse], summary="List all users")
def list_users(limit: int = 20, offset: int = 0):
    """Retrieve all users in the system."""
    return USERS_DB[offset : offset + limit]


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
def get_user(user_id: int):
    """Fetch single user details by user ID."""
    for u in USERS_DB:
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found")


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create new user")
def create_user(user: UserCreate):
    """Register a new user account."""
    new_user = {
        "id": len(USERS_DB) + 1,
        "name": user.name,
        "email": user.email,
        "role": user.role or "member",
    }
    USERS_DB.append(new_user)
    return new_user
