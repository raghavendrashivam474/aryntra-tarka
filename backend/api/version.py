# backend/api/version.py
from fastapi import APIRouter
from datetime import date

router = APIRouter(prefix="/api", tags=["meta"])

APP_VERSION = "1.0.0"
APP_NAME    = "Aryntra Tarka"
SPRINT      = "3.11"

@router.get("/version")
async def get_version() -> dict:
    """
    Return application version metadata.
    Used by the frontend About dialog.
    """
    return {
        "name":       APP_NAME,
        "version":    APP_VERSION,
        "sprint":     SPRINT,
        "build_date": str(date.today()),
        "status":     "stable",
    }
