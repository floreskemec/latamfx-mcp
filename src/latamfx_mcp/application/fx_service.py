"""FX use cases: quotes, time series and currency conversion.

The conversion logic lives here (application policy), built on top of whatever
:class:`FxProvider` adapter is injected. Conversions use the realistic
buy/sell side: to go USD -> ARS you pay the *sell* price; ARS -> USD you receive
the *buy* price.
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl

from latamfx_mcp.domain.errors import UnsupportedConversionError
from latamfx_mcp.domain.models import (
    ConversionResult,
    FxQuote,
    FxSource,
    FxTimeSeries,
)
from latamfx_mcp.ports.fx_provider import FxProvider


class FxService:
    """High-level FX operations exposed (indirectly) as MCP tools."""

    def __init__(self, provider: FxProvider) -> None:
        self._provider = provider

    async def list_sources(self) -> list[FxSource]:
        return await self._provider.list_sources()

    async def get_quote(self, source: str) -> FxQuote:
        return await self._provider.get_quote(source)

    async def get_timeseries(self, source: str) -> FxTimeSeries:
        return await self._provider.get_timeseries(source)

    async def convert(
        self, amount: Decimal, from_currency: str, to_currency: str, source: str
    ) -> ConversionResult:
        """Convert ``amount`` between the base and quote currency of ``source``."""
        quote = await self._provider.get_quote(source)
        base, quote_ccy = quote.base.upper(), quote.quote.upper()
        frm, to = from_currency.upper(), to_currency.upper()

        if {frm, to} != {base, quote_ccy}:
            raise UnsupportedConversionError(frm, to)

        if frm == base:  # e.g. USD -> ARS: pay the sell price
            rate = quote.sell
            converted = amount * rate
        else:  # ARS -> USD: receive the buy price
            rate = quote.buy
            converted = amount / rate

        return ConversionResult(
            amount=amount,
            from_currency=frm,
            to_currency=to,
            converted=converted.quantize(Decimal("0.0001")),
            rate=rate,
            source=source,
            as_of=quote.as_of,
        )

    async def timeseries_stats(self, source: str) -> dict[str, float]:
        """Summary stats over the mid price of a series, computed with Polars.

        Demonstrates a typed domain series flowing into a columnar engine for
        analytics without leaking Polars into the domain layer.
        """
        series = await self._provider.get_timeseries(source)
        if not series.observations:
            return {"count": 0}

        frame = pl.DataFrame(
            {
                "day": [o.day for o in series.observations],
                "mid": [float((o.buy + o.sell) / 2) for o in series.observations],
            }
        ).sort("day")

        deltas = frame.select(pl.col("mid").pct_change().alias("ret")).drop_nulls()
        return {
            "count": int(frame.height),
            "first": float(frame["mid"][0]),
            "last": float(frame["mid"][-1]),
            "min": float(frame["mid"].min()),  # type: ignore[arg-type]
            "max": float(frame["mid"].max()),  # type: ignore[arg-type]
            "mean": float(frame["mid"].mean()),  # type: ignore[arg-type]
            "volatility": float(deltas["ret"].std()) if deltas.height > 1 else 0.0,  # type: ignore[arg-type]
        }
