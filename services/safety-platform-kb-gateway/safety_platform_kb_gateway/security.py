# coding=utf-8
"""Gateway auth helpers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    return Settings.from_env()


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="Gateway API key is not configured.")
    if credentials is None or credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token.")
    return credentials.credentials
