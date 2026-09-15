"""Main application entry point for AI API Documentation Agent backend."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.db.database import init_db
from app.api.health import router as health_router
from app.api.repositories import router as repositories_router
from app.api.documentation import router as documentation_router
from app.api.changes import router as changes_router
from app.api.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered developer tool that monitors a GitHub backend repository, detects API changes from code commits, analyzes changes, automatically updates and validates OpenAPI specifications, and serves live Swagger documentation.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS Configuration - Explicit origins & regex patterns for local & deployed frontends
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|.*\.vercel\.app|.*\.netlify\.app)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception at {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc) if settings.DEBUG else None},
        )

    # Register Routers
    app.include_router(health_router)
    app.include_router(repositories_router)
    app.include_router(documentation_router)
    app.include_router(changes_router)
    app.include_router(webhooks_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
