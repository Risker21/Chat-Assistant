"""Health check and model metadata routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.services.model_registry import model_registry

router = APIRouter(tags=["System"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Liveness and readiness probe including DB connectivity and provider status."""
    settings = get_settings()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    models = model_registry.list_models()
    configured_models = [m.value for m in models if m.configured]

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if db_ok else "error",
        "configured_models": configured_models,
        "vision_enabled": model_registry.is_vision_configured(),
        "web_search_enabled": model_registry.is_search_configured(),
    }


@router.get("/api/v1/models")
def list_models_v1():
    """Return full model catalog with availability and capability flags."""
    models = model_registry.list_models()
    return {
        "models": [m.model_dump() for m in models],
        "web_search_enabled": model_registry.is_search_configured(),
        "vision_enabled": model_registry.is_vision_configured(),
    }


@router.get("/models")
def list_models_legacy():
    """Backward-compatible models endpoint."""
    models = model_registry.list_models()
    return {"models": [m.model_dump() for m in models]}
