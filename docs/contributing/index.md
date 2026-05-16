---
title: Contributing Guide
icon: material/handshake
---

# Contributing

## Reporting issues

Open an issue on [GitHub](https://github.com/TheWinterShadow/The-Curator/issues). Include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Relevant logs (Cloud Run logs, `mcp-remote` output)

## Making changes

1. Fork the repo and create a feature branch.
2. Make your changes — see [Development](development.md) for the local setup.
3. Run `hatch run check` to ensure lint, types, and tests all pass.
4. Open a pull request against `main`.

## Code standards

- **Python 3.12**, typed with `mypy --strict`
- **Ruff** for linting and formatting (`line-length = 100`)
- **Google-style docstrings** on public classes and methods
- Tests live in `tests/` and use `pytest` with `pytest-asyncio`

The CI pipeline enforces all of these on every push.

## Adding a new MCP tool

1. Define the function in `src/the_curator/main.py` decorated with `@mcp.tool()`.
2. Add a docstring — it becomes the tool description visible to MCP clients.
3. Wire any new dependencies through `PodcastGeneration` or `VertexClient` rather than adding ad-hoc SDK calls in `main.py`.
4. Add a test in `tests/test_main.py`.
5. Document the new tool in [API Reference → Server](../api/main.md).
