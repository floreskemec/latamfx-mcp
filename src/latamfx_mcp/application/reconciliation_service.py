"""Reconciliation use case: thin orchestration over the domain engine."""

from __future__ import annotations

from latamfx_mcp.domain.models import LedgerEntry, ReconciliationResult
from latamfx_mcp.domain.reconciliation import (
    AmountDateRule,
    ExactReferenceRule,
    FuzzyDescriptionRule,
    MatchRule,
    ReconciliationEngine,
)


class ReconciliationService:
    """Builds a rule pipeline from simple parameters and runs the engine."""

    def reconcile(
        self,
        left: list[LedgerEntry],
        right: list[LedgerEntry],
        *,
        day_tolerance: int = 2,
        fuzzy_threshold: float = 0.82,
        enable_fuzzy: bool = True,
    ) -> ReconciliationResult:
        rules: list[MatchRule] = [
            ExactReferenceRule(),
            AmountDateRule(day_tolerance=day_tolerance),
        ]
        if enable_fuzzy:
            rules.append(FuzzyDescriptionRule(threshold=fuzzy_threshold))
        engine = ReconciliationEngine(rules=rules)
        return engine.reconcile(left, right)
