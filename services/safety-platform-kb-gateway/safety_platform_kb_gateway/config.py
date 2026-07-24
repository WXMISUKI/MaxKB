# coding=utf-8
"""Gateway configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str
    port: int
    maxkb_base_url: str
    maxkb_username: str
    maxkb_password: str
    maxkb_workspace_id: str
    maxkb_default_embedding_model_id: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=os.getenv("GATEWAY_API_KEY", ""),
            port=int(os.getenv("GATEWAY_PORT", "8092")),
            maxkb_base_url=os.getenv("MAXKB_BASE_URL", "http://localhost:8080/admin/api"),
            maxkb_username=os.getenv("MAXKB_USERNAME", "admin"),
            maxkb_password=os.getenv("MAXKB_PASSWORD", ""),
            maxkb_workspace_id=os.getenv("MAXKB_WORKSPACE_ID", "default"),
            maxkb_default_embedding_model_id=os.getenv("MAXKB_DEFAULT_EMBEDDING_MODEL_ID", ""),
        )

    @property
    def maxkb_ready(self) -> bool:
        return bool(self.maxkb_base_url and self.maxkb_username and self.maxkb_password)
