# ADR 0001 — Hexagonal architecture

- **Status:** Accepted
- **Date:** 2026-06-21

## Context

This is a showcase MCP server, but it should read like production code. The two
pieces with real logic — currency conversion and reconciliation — must be easy to
test and independent of the MCP transport and of any specific upstream API.

## Decision

Adopt a hexagonal (ports & adapters) structure with four layers: `domain`,
`ports`, `application`, `infrastructure`, plus a thin transport module
(`server.py`). The application depends on a `FxProvider` Protocol, never on a
concrete HTTP client.

## Consequences

- The domain and application layers are pure and fast to test (no network, no MCP).
- Adding a new data source is a new adapter implementing `FxProvider`.
- Slightly more files than a flat script — accepted as the point is to demonstrate
  structure, and the indirection pays off in testability.
