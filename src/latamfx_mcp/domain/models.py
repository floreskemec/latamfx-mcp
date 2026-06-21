"""Core domain models.

Money is represented with :class:`decimal.Decimal` to avoid binary float drift,
which matters in financial contexts. Models are immutable (`frozen=True`) so they
behave as value objects.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FxSource(BaseModel):
    """A quotation source (e.g. the Argentine "blue" or "oficial" dollar)."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Stable machine code, e.g. 'blue', 'oficial'.")
    name: str = Field(description="Human-readable name.")
    base: str = Field(default="USD", description="Base currency being quoted.")
    quote: str = Field(default="ARS", description="Currency the base is priced in.")


class FxQuote(BaseModel):
    """A buy/sell quote for one base unit expressed in the quote currency."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="Source code, matches FxSource.code.")
    base: str = Field(default="USD")
    quote: str = Field(default="ARS")
    buy: Decimal = Field(description="Price to buy one unit of base (compra).")
    sell: Decimal = Field(description="Price to sell one unit of base (venta).")
    as_of: datetime = Field(description="Timestamp the quote was last updated.")

    @property
    def mid(self) -> Decimal:
        """Mid price between buy and sell."""
        return (self.buy + self.sell) / Decimal(2)


class FxObservation(BaseModel):
    """A single historical observation in a time series."""

    model_config = ConfigDict(frozen=True)

    day: date
    buy: Decimal
    sell: Decimal


class FxTimeSeries(BaseModel):
    """An ordered historical series for a given source."""

    model_config = ConfigDict(frozen=True)

    source: str
    base: str = "USD"
    quote: str = "ARS"
    observations: tuple[FxObservation, ...]


class ConversionResult(BaseModel):
    """The outcome of converting an amount between two currencies."""

    model_config = ConfigDict(frozen=True)

    amount: Decimal
    from_currency: str
    to_currency: str
    converted: Decimal
    rate: Decimal
    source: str
    as_of: datetime


class LedgerEntry(BaseModel):
    """One side of a transaction to be reconciled.

    Fields mirror the minimum needed by a reconciliation engine: a stable id,
    an optional external reference (e.g. invoice number), an amount and a date,
    plus a free-text description used by fuzzy matching.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    amount: Decimal
    day: date
    reference: str | None = None
    description: str = ""


class MatchedPair(BaseModel):
    """A matched pair of ledger entries with provenance."""

    model_config = ConfigDict(frozen=True)

    left_id: str
    right_id: str
    rule: str = Field(description="Name of the rule that produced the match.")
    score: float = Field(ge=0.0, le=1.0, description="Confidence in [0, 1].")


class ReconciliationResult(BaseModel):
    """Full, auditable output of a reconciliation run."""

    model_config = ConfigDict(frozen=True)

    matched: tuple[MatchedPair, ...]
    unmatched_left: tuple[str, ...]
    unmatched_right: tuple[str, ...]

    @property
    def match_rate(self) -> float:
        """Fraction of left entries that found a match, in [0, 1]."""
        total = len(self.matched) + len(self.unmatched_left)
        return len(self.matched) / total if total else 0.0
