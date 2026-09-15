"""Main entry point for sample FastAPI backend."""

from fastapi import FastAPI
from app.routes.users import router as users_router
from app.routes.products import router as products_router

app = FastAPI(
    title="Sample Store API",
    description="Sample backend demonstrating automated API Documentation Agent tracking.",
    version="1.0.0",
)

app.include_router(users_router)
app.include_router(products_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
