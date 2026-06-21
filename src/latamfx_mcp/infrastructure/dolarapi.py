"""Adapter for public Argentine FX data.

- Latest quotes come from dolarapi.com (https://dolarapi.com).
- Historical series come from ArgentinaDatos (https://argentinadatos.com).

Both are free, key-less, community-maintained public APIs. This adapter is the
only place that knows their wire formats; everything upstream depends on the
:class:`FxProvider` port instead.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from latamfx_mcp.config import Settings
from latamfx_mcp.domain.errors import ProviderError, UnknownSourceError
from latamfx_mcp.domain.models import (
    FxObservation,
    FxQuote,
    FxSource,
    FxTimeSeries,
)
from latamfx_mcp.infrastructure.cache import TTLCache
from latamfx_mcp.infrastructure.http_client import build_client, make_retrying_get

# Stable code -> human label for the dollar "casas" exposed by dolarapi.
KNOWN_SOURCES: dict[str, str] = {
    "oficial": "Dólar Oficial",
    "blue": "Dólar Blue",
    "bolsa": "Dólar MEP (Bolsa)",
    "contadoconliqui": "Dólar CCL (Contado con Liqui)",
    "mayorista": "Dólar Mayorista",
    "cripto": "Dólar Cripto",
    "tarjeta": "Dólar Tarjeta",
}


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        raise ProviderError("Missing numeric field in upstream payload.")
    # Cast through str so JSON floats do not introduce binary drift.
    return Decimal(str(value))


class DolarApiProvider:
    """Concrete :class:`FxProvider` backed by dolarapi + ArgentinaDatos."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.from_env()
        self._client = build_client(self._settings)
        self._get = make_retrying_get(self._settings)
        self._cache: TTLCache[Any] = TTLCache(self._settings.cache_ttl_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> DolarApiProvider:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def list_sources(self) -> list[FxSource]:
        return [FxSource(code=code, name=name) for code, name in KNOWN_SOURCES.items()]

    async def get_quote(self, source: str) -> FxQuote:
        code = source.strip().casefold()
        if code not in KNOWN_SOURCES:
            raise UnknownSourceError(code, list(KNOWN_SOURCES))

        async def _load() -> dict[str, Any]:
            url = f"{self._settings.dolarapi_base_url}/dolares/{code}"
            resp = await self._get(self._client, url)
            data: dict[str, Any] = resp.json()
            return data

        payload = await self._cache.get_or_load(f"quote:{code}", _load)
        return self._parse_quote(code, payload)

    async def get_timeseries(self, source: str) -> FxTimeSeries:
        code = source.strip().casefold()
        if code not in KNOWN_SOURCES:
            raise UnknownSourceError(code, list(KNOWN_SOURCES))

        async def _load() -> list[dict[str, Any]]:
            url = f"{self._settings.argentinadatos_base_url}/cotizaciones/dolares/{code}"
            resp = await self._get(self._client, url)
            data: list[dict[str, Any]] = resp.json()
            return data

        rows = await self._cache.get_or_load(f"series:{code}", _load)
        observations = tuple(
            FxObservation(
                day=date.fromisoformat(row["fecha"]),
                buy=_to_decimal(row.get("compra")),
                sell=_to_decimal(row.get("venta")),
            )
            for row in rows
            if row.get("compra") is not None and row.get("venta") is not None
        )
        return FxTimeSeries(source=code, observations=observations)

    @staticmethod
    def _parse_quote(code: str, payload: dict[str, Any]) -> FxQuote:
        raw_ts = payload.get("fechaActualizacion")
        try:
            as_of = (
                datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if isinstance(raw_ts, str)
                else datetime.now()
            )
        except ValueError:
            as_of = datetime.now()
        return FxQuote(
            source=code,
            buy=_to_decimal(payload.get("compra")),
            sell=_to_decimal(payload.get("venta")),
            as_of=as_of,
        )
