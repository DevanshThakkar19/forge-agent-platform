"""API router."""

from fastapi import APIRouter

from app.api.routes import health, metrics, runs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(runs.router)
api_router.include_router(metrics.router)
