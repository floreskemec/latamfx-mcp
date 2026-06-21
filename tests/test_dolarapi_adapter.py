"""Contract tests for the dolarapi/ArgentinaDatos adapter using mocked HTTP."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from latamfx_mcp.config import Settings
from latamfx_mcp.domain.errors import UnknownSourceError
from latamfx_mcp.infrastructure.dolarapi import DolarApiProvider

SETTINGS = Settings(http_max_retries=2, cache_ttl_seconds=0.0)


@pytest.fixture
async def provider() -> DolarApiProvider:
    p = DolarApiProvider(settings=SETTINGS)
    yield p
    await p.aclose()


@respx.mock
async def test_get_quote_parses_payload(provider: DolarApiProvider) -> None:
    respx.get(f"{SETTINGS.dolarapi_base_url}/dolares/blue").mock(
        return_value=httpx.Response(
            200,
            json={
                "moneda": "USD",
                "casa": "blue",
                "nombre": "Blue",
                "compra": 1200.5,
                "venta": 1250.5,
                "fechaActualizacion": "2026-01-31T15:00:00.000Z",
            },
        )
    )
    quote = await provider.get_quote("blue")
    assert quote.source == "blue"
    assert quote.buy == Decimal("1200.5")
    assert quote.sell == Decimal("1250.5")
    assert quote.mid == Decimal("1225.5")


@respx.mock
async def test_get_quote_retries_on_5xx(provider: DolarApiProvider) -> None:
    route = respx.get(f"{SETTINGS.dolarapi_base_url}/dolares/oficial")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(
            200,
            json={"compra": 900, "venta": 950, "fechaActualizacion": "2026-01-31T00:00:00Z"},
        ),
    ]
    quote = await provider.get_quote("oficial")
    assert quote.sell == Decimal("950")
    assert route.call_count == 2


async def test_unknown_source_rejected_without_http(provider: DolarApiProvider) -> None:
    with pytest.raises(UnknownSourceError):
        await provider.get_quote("not-a-source")


@respx.mock
async def test_get_timeseries_parses_rows(provider: DolarApiProvider) -> None:
    respx.get(f"{SETTINGS.argentinadatos_base_url}/cotizaciones/dolares/blue").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"casa": "blue", "fecha": "2026-01-01", "compra": 1000, "venta": 1050},
                {"casa": "blue", "fecha": "2026-01-02", "compra": 1010, "venta": 1060},
                {"casa": "blue", "fecha": "2026-01-03", "compra": None, "venta": None},
            ],
        )
    )
    series = await provider.get_timeseries("blue")
    assert len(series.observations) == 2  # null row skipped
    assert series.observations[0].buy == Decimal("1000")
