"""
Aryntra Tarka - Application Entry Point

Sprint 3.11 - CORS extended to include Vite dev server (5173).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import api_router
from backend.config.settings import settings
from backend.utils.logger import get_logger
from backend.api.version import router as version_router

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
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api")
app.include_router(version_router)

logger.info("Aryntra Tarka started. Environment: %s", settings.app_env)
