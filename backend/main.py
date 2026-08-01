"""
Aryntra Tarka - Application Entry Point

Sprint 3.11 - CORS extended to include Vite dev server (5173).
Layer 2    - Runtime HTTP client lifecycle managed via startup/shutdown hooks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import api_router
from backend.api.version import router as version_router
from backend.config.settings import settings
from backend.runtime.performance.http_client import RuntimeHttpClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Runtime HTTP client initialising.")
    RuntimeHttpClient.get_client()
    yield
    logger.info("Runtime HTTP client shutting down.")
    await RuntimeHttpClient.close()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description="A clean, modular AI backend framework.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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