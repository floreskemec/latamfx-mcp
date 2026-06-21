"""Auditable multi-rule reconciliation engine.

This is a sanitized, generic version of matching engines used in real
intercompany / bank reconciliation work. Rules run in priority order; once a
right-side entry is consumed it cannot match again, which keeps the result a
valid one-to-one assignment and makes every match traceable to the rule that
produced it.

The engine is pure (no I/O), deterministic and fully unit-testable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from difflib import SequenceMatcher

from .models import LedgerEntry, MatchedPair, ReconciliationResult


class MatchRule(ABC):
    """A single matching strategy.

    Implementations return the best candidate index from ``available`` for a
    given left entry, or ``None``. A ``score`` in [0, 1] expresses confidence.
    """

    name: str

    @abstractmethod
    def find(self, left: LedgerEntry, candidates: list[LedgerEntry]) -> tuple[int, float] | None:
        """Return ``(candidate_index, score)`` for the best match, or ``None``."""


class ExactReferenceRule(MatchRule):
    """Match when both entries share a non-empty external reference."""

    name = "exact_reference"

    def find(self, left: LedgerEntry, candidates: list[LedgerEntry]) -> tuple[int, float] | None:
        if not left.reference:
            return None
        ref = left.reference.strip().casefold()
        for idx, cand in enumerate(candidates):
            if cand.reference and cand.reference.strip().casefold() == ref:
                return idx, 1.0
        return None


class AmountDateRule(MatchRule):
    """Match on equal amount within a tolerance window of days.

    Score decays linearly with the day gap so a same-day match scores higher
    than one at the edge of the window.
    """

    name = "amount_date"

    def __init__(self, day_tolerance: int = 2) -> None:
        if day_tolerance < 0:
            raise ValueError("day_tolerance must be >= 0")
        self.day_tolerance = day_tolerance

    def find(self, left: LedgerEntry, candidates: list[LedgerEntry]) -> tuple[int, float] | None:
        best: tuple[int, float] | None = None
        for idx, cand in enumerate(candidates):
            if cand.amount != left.amount:
                continue
            gap = abs((cand.day - left.day).days)
            if gap > self.day_tolerance:
                continue
            score = 1.0 - (gap / (self.day_tolerance + 1))
            if best is None or score > best[1]:
                best = (idx, round(score, 4))
        return best


class FuzzyDescriptionRule(MatchRule):
    """Match on equal amount plus similar description above a threshold.

    Useful when references are missing but human-entered descriptions overlap
    (e.g. "PAGO PROVEEDOR ACME" vs "Acme proveedor pago"). Similarity uses the
    stdlib SequenceMatcher to keep the dependency surface minimal; swap in
    rapidfuzz for large volumes.
    """

    name = "fuzzy_description"

    def __init__(self, threshold: float = 0.82, amount_tolerance: Decimal | None = None) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold must be in (0, 1]")
        self.threshold = threshold
        self.amount_tolerance = amount_tolerance or Decimal("0")

    def find(self, left: LedgerEntry, candidates: list[LedgerEntry]) -> tuple[int, float] | None:
        if not left.description:
            return None
        left_desc = left.description.strip().casefold()
        best: tuple[int, float] | None = None
        for idx, cand in enumerate(candidates):
            if abs(cand.amount - left.amount) > self.amount_tolerance:
                continue
            if not cand.description:
                continue
            ratio = SequenceMatcher(None, left_desc, cand.description.strip().casefold()).ratio()
            if ratio >= self.threshold and (best is None or ratio > best[1]):
                best = (idx, round(ratio, 4))
        return best


def default_rules() -> list[MatchRule]:
    """The standard rule pipeline in descending priority/confidence order."""
    return [ExactReferenceRule(), AmountDateRule(day_tolerance=2), FuzzyDescriptionRule()]


class ReconciliationEngine:
    """Runs a pipeline of rules to produce a one-to-one reconciliation."""

    def __init__(self, rules: list[MatchRule] | None = None) -> None:
        self.rules = rules if rules is not None else default_rules()

    def reconcile(self, left: list[LedgerEntry], right: list[LedgerEntry]) -> ReconciliationResult:
        """Match ``left`` against ``right``, each right entry used at most once."""
        remaining: list[LedgerEntry | None] = list(right)
        matched: list[MatchedPair] = []
        unmatched_left: list[str] = []

        for entry in left:
            pair = self._match_one(entry, remaining)
            if pair is None:
                unmatched_left.append(entry.id)
            else:
                matched.append(pair)

        unmatched_right = [e.id for e in remaining if e is not None]
        return ReconciliationResult(
            matched=tuple(matched),
            unmatched_left=tuple(unmatched_left),
            unmatched_right=tuple(unmatched_right),
        )

    def _match_one(
        self, entry: LedgerEntry, remaining: list[LedgerEntry | None]
    ) -> MatchedPair | None:
        # Build the live candidate list (index-aligned to ``remaining``).
        for rule in self.rules:
            live_indices = [i for i, c in enumerate(remaining) if c is not None]
            candidates = [remaining[i] for i in live_indices]
            hit = rule.find(entry, candidates)  # type: ignore[arg-type]
            if hit is None:
                continue
            local_idx, score = hit
            global_idx = live_indices[local_idx]
            consumed = remaining[global_idx]
            assert consumed is not None  # narrowed by live_indices construction
            remaining[global_idx] = None  # consume so it cannot match again
            return MatchedPair(
                left_id=entry.id,
                right_id=consumed.id,
                rule=rule.name,
                score=score,
            )
        return None
