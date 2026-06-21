"""Tests for FX application services using the fake provider."""

from __future__ import annotations

from decimal import Decimal

import pytest

from latamfx_mcp.application.fx_service import FxService
from latamfx_mcp.domain.errors import UnknownSourceError, UnsupportedConversionError


async def test_list_sources(fake_provider) -> None:
    service = FxService(fake_provider)
    sources = await service.list_sources()
    assert {s.code for s in sources} == {"oficial", "blue"}


async def test_convert_usd_to_ars_uses_sell(fake_provider) -> None:
    service = FxService(fake_provider)
    result = await service.convert(Decimal("10"), "USD", "ARS", "oficial")
    assert result.rate == Decimal("950")  # sell side
    assert result.converted == Decimal("9500.0000")


async def test_convert_ars_to_usd_uses_buy(fake_provider) -> None:
    service = FxService(fake_provider)
    result = await service.convert(Decimal("9000"), "ARS", "USD", "oficial")
    assert result.rate == Decimal("900")  # buy side
    assert result.converted == Decimal("10.0000")


async def test_convert_rejects_unsupported_pair(fake_provider) -> None:
    service = FxService(fake_provider)
    with pytest.raises(UnsupportedConversionError):
        await service.convert(Decimal("1"), "USD", "BRL", "oficial")


async def test_unknown_source_raises(fake_provider) -> None:
    service = FxService(fake_provider)
    with pytest.raises(UnknownSourceError):
        await service.get_quote("does-not-exist")


async def test_timeseries_stats(fake_provider) -> None:
    service = FxService(fake_provider)
    stats = await service.timeseries_stats("oficial")
    assert stats["count"] == 5
    assert stats["min"] < stats["max"]
    assert "volatility" in stats
