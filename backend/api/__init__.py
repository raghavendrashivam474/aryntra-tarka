"""
API package for Aryntra Tarka.

Registers all routers and exposes the combined router
to the application entry point.
"""

from fastapi import APIRouter
from backend.api.routes.health import router as health_router
from backend.api.routes.chat import router as chat_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
