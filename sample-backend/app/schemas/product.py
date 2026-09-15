"""Product schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    title: str = Field(..., description="Product title")
    price: float = Field(..., description="Price in USD")
    in_stock: bool = Field(default=True)


class ProductResponse(BaseModel):
    id: int
    title: str
    price: float
    in_stock: bool
