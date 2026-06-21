"""HTTP helpers: a configured httpx client and a retry policy.

Retries use exponential backoff with jitter on transport errors and 5xx
responses only; 4xx are surfaced immediately because retrying them is pointless.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from latamfx_mcp.config import Settings


def build_client(settings: Settings) -> httpx.AsyncClient:
    """Create an AsyncClient with sane timeouts and a descriptive user agent."""
    return httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
    )


class RetryableStatusError(Exception):
    """Wraps a retryable (5xx) upstream response."""


def make_retrying_get(
    settings: Settings,
) -> Callable[[httpx.AsyncClient, str], Awaitable[httpx.Response]]:
    """Return an async ``get(url)`` that retries transient failures."""

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, RetryableStatusError)),
        stop=stop_after_attempt(settings.http_max_retries),
        wait=wait_exponential_jitter(initial=0.2, max=3.0),
        reraise=True,
    )
    async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
        response = await client.get(url)
        if response.status_code >= 500:
            raise RetryableStatusError(f"{response.status_code} from {url}")
        response.raise_for_status()
        return response

    return _get
