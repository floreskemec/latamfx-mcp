# ADR 0003 — Priority-ordered reconciliation rule engine

- **Status:** Accepted
- **Date:** 2026-06-21

## Context

The reconciliation tool is the differentiating feature: a generic, sanitized
version of intercompany / bank reconciliation engines used in real fintech work.
It must produce results that a human auditor can trust and explain.

## Decision

Model each matching strategy as a `MatchRule` with a single `find` method that
returns a candidate and a confidence score in `[0, 1]`. Rules run in priority
order (exact reference → amount+date → fuzzy description). Each right-side entry
is consumed at most once, so the output is a valid one-to-one assignment and
every match records the rule that produced it.

Similarity uses the standard library's `difflib.SequenceMatcher` to keep the
dependency surface small; `rapidfuzz` is the drop-in upgrade for large volumes.

## Consequences

- **Auditable:** every match carries its rule and score; nothing is a black box.
- **Deterministic & pure:** trivially unit-tested, no I/O.
- **Greedy, not globally optimal:** consuming the first match per rule is simpler
  and matches how analysts reconcile by hand. A future rule could add Hungarian /
  optimal assignment if needed — the `MatchRule` interface would not change.
- **Extensible:** new strategies (e.g. amount within a percentage tolerance) are
  added without touching the engine.
