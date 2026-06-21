"""Tests for the reconciliation application service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from latamfx_mcp.application.reconciliation_service import ReconciliationService
from latamfx_mcp.domain.models import LedgerEntry


def _entry(id_: str, amount: str, day: int, **kw) -> LedgerEntry:
    return LedgerEntry(id=id_, amount=Decimal(amount), day=date(2026, 1, day), **kw)


def test_service_runs_full_pipeline() -> None:
    service = ReconciliationService()
    left = [
        _entry("L1", "100", 1, reference="INV-1"),
        _entry("L2", "200", 5, description="pago acme"),
    ]
    right = [
        _entry("R1", "100", 3, reference="INV-1"),
        _entry("R2", "200", 5, description="ACME pago"),
    ]
    result = service.reconcile(left, right, fuzzy_threshold=0.4)
    assert result.match_rate == 1.0
    rules = {m.rule for m in result.matched}
    assert "exact_reference" in rules


def test_service_can_disable_fuzzy() -> None:
    service = ReconciliationService()
    left = [_entry("L1", "200", 5, description="pago acme")]
    right = [_entry("R1", "200", 9, description="ACME pago")]  # 4 days apart, no ref
    result = service.reconcile(left, right, day_tolerance=2, enable_fuzzy=False)
    assert result.matched == ()
