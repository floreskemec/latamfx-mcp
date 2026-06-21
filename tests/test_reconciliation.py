"""Unit tests for the pure reconciliation engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from latamfx_mcp.domain.models import LedgerEntry
from latamfx_mcp.domain.reconciliation import (
    AmountDateRule,
    FuzzyDescriptionRule,
    ReconciliationEngine,
)


def entry(id_: str, amount: str, day: int, reference=None, description="") -> LedgerEntry:
    return LedgerEntry(
        id=id_,
        amount=Decimal(amount),
        day=date(2026, 1, day),
        reference=reference,
        description=description,
    )


def test_exact_reference_takes_priority() -> None:
    left = [entry("L1", "100.00", 1, reference="INV-1")]
    right = [
        entry("R1", "100.00", 1, reference="OTHER"),
        entry("R2", "100.00", 3, reference="INV-1"),
    ]
    result = ReconciliationEngine().reconcile(left, right)
    assert len(result.matched) == 1
    pair = result.matched[0]
    assert pair.right_id == "R2"
    assert pair.rule == "exact_reference"
    assert pair.score == 1.0


def test_amount_date_within_tolerance() -> None:
    left = [entry("L1", "250.00", 10)]
    right = [entry("R1", "250.00", 12)]  # 2 days apart
    result = ReconciliationEngine(rules=[AmountDateRule(day_tolerance=2)]).reconcile(left, right)
    assert len(result.matched) == 1
    assert result.matched[0].rule == "amount_date"
    assert 0.0 < result.matched[0].score < 1.0


def test_amount_date_outside_tolerance_does_not_match() -> None:
    left = [entry("L1", "250.00", 10)]
    right = [entry("R1", "250.00", 20)]
    result = ReconciliationEngine(rules=[AmountDateRule(day_tolerance=2)]).reconcile(left, right)
    assert result.matched == ()
    assert result.unmatched_left == ("L1",)
    assert result.unmatched_right == ("R1",)


def test_fuzzy_description_matches_similar_text() -> None:
    left = [entry("L1", "500.00", 5, description="PAGO PROVEEDOR ACME SA")]
    right = [entry("R1", "500.00", 5, description="Acme S.A. proveedor - pago")]
    rule = FuzzyDescriptionRule(threshold=0.4)
    result = ReconciliationEngine(rules=[rule]).reconcile(left, right)
    assert len(result.matched) == 1
    assert result.matched[0].rule == "fuzzy_description"


def test_right_entry_consumed_only_once() -> None:
    left = [entry("L1", "100.00", 1, reference="A"), entry("L2", "100.00", 1, reference="A")]
    right = [entry("R1", "100.00", 1, reference="A")]
    result = ReconciliationEngine().reconcile(left, right)
    assert len(result.matched) == 1
    assert result.unmatched_left == ("L2",)


def test_match_rate() -> None:
    left = [entry("L1", "10", 1, reference="X"), entry("L2", "20", 1)]
    right = [entry("R1", "10", 1, reference="X")]
    result = ReconciliationEngine().reconcile(left, right)
    assert result.match_rate == 0.5
