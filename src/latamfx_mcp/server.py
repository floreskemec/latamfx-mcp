"""MCP server entrypoint.

Exposes public LatAm FX data and an auditable reconciliation engine as MCP
tools and resources, usable from Claude Desktop, Claude Code or any MCP client.

Run locally:
    uv run latamfx-mcp            # stdio transport (default)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from latamfx_mcp.application.fx_service import FxService
from latamfx_mcp.application.reconciliation_service import ReconciliationService
from latamfx_mcp.domain.errors import DomainError
from latamfx_mcp.domain.models import LedgerEntry
from latamfx_mcp.infrastructure.dolarapi import DolarApiProvider

mcp = FastMCP(
    "latamfx",
    instructions=(
        "Tools for public LatAm FX data (Argentine dollar quotes and history) "
        "and an auditable transaction reconciliation engine. All data comes from "
        "free public APIs; no credentials required."
    ),
)

# Single shared provider/service instances for the process lifetime.
_provider = DolarApiProvider()
_fx = FxService(_provider)
_recon = ReconciliationService()


def _to_decimal(value: float | str) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise ValueError(f"Not a valid number: {value!r}") from exc


class ReconcileEntry(BaseModel):
    """One ledger entry for the reconcile tool."""

    id: str
    amount: float
    day: str = Field(description="ISO date, e.g. 2026-01-31.")
    reference: str | None = None
    description: str = ""


@mcp.tool()
async def list_fx_sources() -> list[dict[str, str]]:
    """List the supported FX sources (Argentine dollar variants)."""
    sources = await _fx.list_sources()
    return [s.model_dump() for s in sources]


@mcp.tool()
async def get_fx_quote(source: str) -> dict[str, Any]:
    """Get the latest buy/sell quote for an FX source (e.g. 'blue', 'oficial')."""
    try:
        quote = await _fx.get_quote(source)
    except DomainError as exc:
        return {"error": str(exc)}
    return quote.model_dump(mode="json")


@mcp.tool()
async def get_fx_timeseries(
    source: str,
    last_n: Annotated[int, Field(ge=1, le=5000)] = 30,
) -> dict[str, Any]:
    """Get the historical buy/sell series for a source (most recent ``last_n``)."""
    try:
        series = await _fx.get_timeseries(source)
    except DomainError as exc:
        return {"error": str(exc)}
    obs = [o.model_dump(mode="json") for o in series.observations[-last_n:]]
    return {
        "source": series.source,
        "base": series.base,
        "quote": series.quote,
        "observations": obs,
    }


@mcp.tool()
async def get_fx_stats(source: str) -> dict[str, Any]:
    """Summary statistics (min/max/mean/volatility) of a source's mid price."""
    try:
        return await _fx.timeseries_stats(source)
    except DomainError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def convert(
    amount: float,
    from_currency: str,
    to_currency: str,
    source: str = "oficial",
) -> dict[str, Any]:
    """Convert an amount between currencies using a source's quote (e.g. USD<->ARS)."""
    try:
        result = await _fx.convert(_to_decimal(amount), from_currency, to_currency, source)
    except DomainError as exc:
        return {"error": str(exc)}
    return result.model_dump(mode="json")


@mcp.tool()
async def reconcile(
    left: list[ReconcileEntry],
    right: list[ReconcileEntry],
    day_tolerance: Annotated[int, Field(ge=0, le=30)] = 2,
    fuzzy_threshold: Annotated[float, Field(gt=0, le=1)] = 0.82,
    enable_fuzzy: bool = True,
) -> dict[str, Any]:
    """Reconcile two ledgers with a multi-rule engine (exact ref, amount+date, fuzzy).

    Returns matched pairs (with the rule and a confidence score), unmatched ids
    on each side, and the overall match rate.
    """

    def to_domain(entries: list[ReconcileEntry]) -> list[LedgerEntry]:
        return [
            LedgerEntry(
                id=e.id,
                amount=_to_decimal(e.amount),
                day=date.fromisoformat(e.day),
                reference=e.reference,
                description=e.description,
            )
            for e in entries
        ]

    try:
        result = _recon.reconcile(
            to_domain(left),
            to_domain(right),
            day_tolerance=day_tolerance,
            fuzzy_threshold=fuzzy_threshold,
            enable_fuzzy=enable_fuzzy,
        )
    except (DomainError, ValueError) as exc:
        return {"error": str(exc)}

    return {
        "matched": [m.model_dump() for m in result.matched],
        "unmatched_left": list(result.unmatched_left),
        "unmatched_right": list(result.unmatched_right),
        "match_rate": round(result.match_rate, 4),
    }


@mcp.resource("fx://sources")
async def sources_resource() -> str:
    """The FX source catalog as a human-readable list."""
    sources = await _fx.list_sources()
    return "\n".join(f"{s.code}: {s.name} ({s.base}/{s.quote})" for s in sources)


def main() -> None:
    """Console-script entrypoint: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
