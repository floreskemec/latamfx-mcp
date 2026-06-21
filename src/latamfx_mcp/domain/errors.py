"""Domain-level errors. Transport/adapters translate these into MCP errors."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""


class UnknownSourceError(DomainError):
    """Raised when a requested FX source code is not supported."""

    def __init__(self, code: str, available: list[str]) -> None:
        self.code = code
        self.available = available
        super().__init__(f"Unknown FX source '{code}'. Available: {', '.join(sorted(available))}")


class UnsupportedConversionError(DomainError):
    """Raised when a currency pair cannot be converted with the available data."""

    def __init__(self, base: str, quote: str) -> None:
        self.base = base
        self.quote = quote
        super().__init__(f"Unsupported conversion {base}->{quote}.")


class ProviderError(DomainError):
    """Raised when an upstream data provider fails or returns invalid data."""
