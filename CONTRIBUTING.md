# Contributing

Thanks for your interest! This is primarily a reference / showcase project, but
issues and PRs are welcome.

## Development setup

```bash
uv sync
uv run pytest
```

## Before opening a PR

Please make sure the full quality gate passes locally (it is the same one CI runs):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

## Guidelines

- Keep the domain layer pure — no I/O, no MCP, no HTTP.
- New data sources go in `infrastructure/` as adapters implementing the
  `FxProvider` port.
- Add tests for new behaviour; the adapter layer is tested against mocked HTTP
  (`respx`), never the live network.
- Record notable design decisions as a new ADR in `docs/adr/`.

By contributing you agree your contributions are licensed under the MIT License.
