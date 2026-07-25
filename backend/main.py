"""
Aryntra Tarka - Application Entry Point

Responsibilities:
- Initialise the FastAPI application
- Configure application metadata
- Register API routers
- Expose no business or AI logic
"""

from fastapi import FastAPI
from backend.api import api_router
from backend.config.settings import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description="A clean, modular AI backend framework.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router)

logger.info("Aryntra Tarka started. Environment: %s", settings.app_env)