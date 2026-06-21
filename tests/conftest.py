"""Shared fixtures: an in-memory fake FX provider for fast, deterministic tests."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from latamfx_mcp.domain.errors import UnknownSourceError
from latamfx_mcp.domain.models import (
    FxObservation,
    FxQuote,
    FxSource,
    FxTimeSeries,
)


class FakeFxProvider:
    """Implements the FxProvider port without any network access."""

    def __init__(self) -> None:
        self._sources = {
            "oficial": "Dólar Oficial",
            "blue": "Dólar Blue",
        }

    async def list_sources(self) -> list[FxSource]:
        return [FxSource(code=c, name=n) for c, n in self._sources.items()]

    async def get_quote(self, source: str) -> FxQuote:
        if source not in self._sources:
            raise UnknownSourceError(source, list(self._sources))
        buy, sell = (
            (Decimal("900"), Decimal("950"))
            if source == "oficial"
            else (
                Decimal("1200"),
                Decimal("1250"),
            )
        )
        return FxQuote(source=source, buy=buy, sell=sell, as_of=datetime(2026, 1, 31, 12, 0))

    async def get_timeseries(self, source: str) -> FxTimeSeries:
        if source not in self._sources:
            raise UnknownSourceError(source, list(self._sources))
        obs = tuple(
            FxObservation(
                day=date(2026, 1, day),
                buy=Decimal(900 + day),
                sell=Decimal(950 + day),
            )
            for day in range(1, 6)
        )
        return FxTimeSeries(source=source, observations=obs)


@pytest.fixture
def fake_provider() -> FakeFxProvider:
    return FakeFxProvider()
