"""Request dependencies."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.config import Settings
from app.services.runs import RunService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_run_service(request: Request) -> RunService:
    return request.app.state.run_service


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    settings: Settings = request.app.state.settings
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
