"""User schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    role: Optional[str] = Field(default="member", description="User role")


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
