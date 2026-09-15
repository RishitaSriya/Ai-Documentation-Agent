"""Product routes."""

from typing import List
from fastapi import APIRouter
from app.schemas.product import ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])

PRODUCTS_DB = [
    {"id": 1, "title": "Developer Mechanical Keyboard", "price": 149.99, "in_stock": True},
    {"id": 2, "title": "4K Ultra-Wide Monitor", "price": 499.00, "in_stock": True},
]


@router.get("", response_model=List[ProductResponse], summary="List all products")
def list_products():
    """Retrieve catalog products."""
    return PRODUCTS_DB
