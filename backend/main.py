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

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Aryntra Tarka",
    description="A clean, modular AI backend framework.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router)