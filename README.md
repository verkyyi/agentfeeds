# Agent Feeds

Agent Feeds is a small local protocol for giving an AI agent ambient awareness of subscribed external data streams through files.

This repository currently contains the v0.3 reference skeleton:

- `bundle/` contains the agent skill and command entrypoints.
- `catalog/` contains starter stream definitions and schemas.
- `scripts/` contains catalog build and validation helpers.
- `tests/` contains the initial test scaffold.
- `SPEC.md` is the implementation spec.

## Development

Install development dependencies:

```bash
uv sync
```

Build the catalog index:

```bash
uv run python scripts/build-index.py
```

Validate a stream:

```bash
uv run python scripts/validate-stream.py catalog/streams/weather/openmeteo-current.yaml
```

Run tests:

```bash
uv run pytest
```

## Status

This is a basic skeleton. The fetcher has filesystem and catalog-regeneration scaffolding, but full adapter execution is still to be implemented from `SPEC.md`.
