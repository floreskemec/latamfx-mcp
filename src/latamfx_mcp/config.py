"""Runtime configuration, read from environment variables with safe defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Immutable settings for the server and its adapters."""

    dolarapi_base_url: str = "https://dolarapi.com/v1"
    argentinadatos_base_url: str = "https://api.argentinadatos.com/v1"
    http_timeout_seconds: float = 10.0
    http_max_retries: int = 3
    cache_ttl_seconds: float = 60.0
    user_agent: str = "latamfx-mcp/0.1 (+https://github.com/floreskemec/latamfx-mcp)"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            dolarapi_base_url=os.getenv("LATAMFX_DOLARAPI_URL", cls.dolarapi_base_url),
            argentinadatos_base_url=os.getenv(
                "LATAMFX_ARGENTINADATOS_URL", cls.argentinadatos_base_url
            ),
            http_timeout_seconds=float(os.getenv("LATAMFX_HTTP_TIMEOUT", cls.http_timeout_seconds)),
            http_max_retries=int(os.getenv("LATAMFX_HTTP_RETRIES", cls.http_max_retries)),
            cache_ttl_seconds=float(os.getenv("LATAMFX_CACHE_TTL", cls.cache_ttl_seconds)),
        )
