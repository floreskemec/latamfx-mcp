# ADR 0002 — Public, key-less data sources only

- **Status:** Accepted
- **Date:** 2026-06-21

## Context

The server must be safe to publish and run by anyone, with zero client data and
no secret management. It also needs both *latest* quotes and *historical* series.

## Decision

Use two free, community-maintained public APIs:

- **dolarapi.com** for latest Argentine dollar quotes.
- **ArgentinaDatos** for historical series.

No API keys, no auth, no PII. The adapter caches responses with a short TTL to be
polite to these free services and to keep tool latency low.

## Consequences

- Anyone can clone and run the server immediately.
- The project depends on third-party uptime; the cache and retry policy soften
  transient failures, and unknown sources fail fast without a network call.
- If a provider changes its wire format, the blast radius is a single adapter
  module, covered by contract tests against mocked HTTP.
