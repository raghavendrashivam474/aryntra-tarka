"""
Health and root endpoints for Aryntra Tarka.

Responsibilities:
- Confirm the application is reachable
- Confirm the application is running
- Expose no business or AI logic
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class RootResponse(BaseModel):
    name: str
    version: str
    status: str


class HealthResponse(BaseModel):
    status: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=RootResponse,
    summary="Root",
    description="Returns basic application identity information.",
    tags=["System"],
)
async def root() -> RootResponse:
    return RootResponse(
        name="Aryntra Tarka",
        version="0.1.0",
        status="online",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Confirms the application is running and reachable.",
    tags=["System"],
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        message="Aryntra Tarka is running.",
    )