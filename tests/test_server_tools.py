"""Smoke tests for the MCP server tool functions.

FastMCP keeps the decorated functions directly callable, so we invoke them as
plain coroutines. The pure tools (reconcile) are exercised directly; network
tools are verified by swapping the module-level service for the fake provider.
"""

from __future__ import annotations

import latamfx_mcp.server as server
from latamfx_mcp.application.fx_service import FxService
from latamfx_mcp.server import ReconcileEntry, get_fx_quote, reconcile

from .conftest import FakeFxProvider


async def test_reconcile_tool_pure() -> None:
    left = [ReconcileEntry(id="L1", amount=100.0, day="2026-01-01", reference="INV-1")]
    right = [ReconcileEntry(id="R1", amount=100.0, day="2026-01-01", reference="INV-1")]
    result = await reconcile(left=left, right=right)
    assert result["match_rate"] == 1.0
    assert result["matched"][0]["rule"] == "exact_reference"


async def test_convert_tool_with_fake(monkeypatch) -> None:
    monkeypatch.setattr(server, "_fx", FxService(FakeFxProvider()))
    result = await server.convert(
        amount=10.0, from_currency="USD", to_currency="ARS", source="oficial"
    )
    assert result["converted"] == "9500.0000"


async def test_get_fx_quote_tool_unknown_source_returns_error(monkeypatch) -> None:
    monkeypatch.setattr(server, "_fx", FxService(FakeFxProvider()))
    result = await get_fx_quote(source="nope")
    assert "error" in result
