"""Port for upstream FX data providers.

The application depends on this Protocol, not on any concrete HTTP client, so
adapters (dolarapi, BCRA, a fake for tests) are interchangeable.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from latamfx_mcp.domain.models import FxQuote, FxSource, FxTimeSeries


@runtime_checkable
class FxProvider(Protocol):
    """Read-only access to FX quotes and historical series."""

    async def list_sources(self) -> list[FxSource]:
        """Return the catalog of supported sources."""
        ...

    async def get_quote(self, source: str) -> FxQuote:
        """Return the latest quote for ``source``."""
        ...

    async def get_timeseries(self, source: str) -> FxTimeSeries:
        """Return the full available historical series for ``source``."""
        ...
