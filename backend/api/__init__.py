# coding: utf-8
"""
api/__init__.py

Registers all routers and exposes the combined router
to the application entry point.

Sprint 3.20.1 - Added runtime WebSocket router.
v1.5         - Added plugins router.
"""

from fastapi import APIRouter

from backend.api.routes.health import router as health_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.runtime_ws import router as runtime_router
from backend.api.routes.plugins import router as plugins_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(runtime_router)
api_router.include_router(plugins_router)