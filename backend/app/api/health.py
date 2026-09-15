"""Health check and status API endpoints."""

import os
import sys
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app import __version__

router = APIRouter(tags=["Health"])

START_TIME = datetime.now(timezone.utc)


@router.get("/health", summary="Application Health Check")
def health_check():
    """Health check endpoint returning system status and configuration."""
    uptime_seconds = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": __version__,
        "environment": settings.APP_ENV,
        "uptime_seconds": round(uptime_seconds, 2),
        "llm_provider": settings.LLM_PROVIDER,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "database": "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "custom",
        "storage_ready": os.path.exists(settings.STORAGE_PATH),
        "python_version": sys.version.split()[0],
    }
