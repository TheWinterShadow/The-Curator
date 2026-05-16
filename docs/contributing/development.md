---
title: Development Setup
icon: material/code-braces
---

# Development Setup

## Prerequisites

- Python 3.12
- [Hatch](https://hatch.pypa.io/latest/install/) (`pipx install hatch`)
- A GCP project with Vertex AI and Cloud Storage enabled
- Application Default Credentials (`gcloud auth application-default login`)

## Clone and install

```bash
git clone https://github.com/TheWinterShadow/The-Curator.git
cd The-Curator
hatch env create
```

## Environment

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export ALLOWED_EMAIL="you@example.com"
export SERVER_URL="http://localhost:8000"
```

## Run the server

```bash
hatch run start
```

The server starts with `--reload` — file changes restart it automatically.

## Tests

```bash
hatch run test               # run all tests
hatch run pytest tests/auth  # run a specific directory
```

Tests use `pytest-asyncio` in auto mode. Mocks are provided in `tests/conftest.py` for GCS and Vertex AI clients.

## Lint and format

```bash
hatch run lint    # ruff check
hatch run fmt     # ruff format (auto-fix)
hatch run check   # lint + typecheck + test
```

## Type checking

```bash
hatch run typecheck   # mypy --strict on src/
```

The codebase runs `mypy` in strict mode. All new code must be fully typed.

## Project structure

```text
src/the_curator/
├── main.py                  # FastMCP server and tool definitions
├── podcast_generation.py    # Transcript and audio synthesis pipeline
├── auth/
│   └── provider.py          # Google OAuth 2.1 provider
└── utils/
    └── vertex_client.py     # Vertex AI SDK wrapper

tests/
├── conftest.py              # Shared fixtures and mocks
├── test_main.py             # Tool endpoint tests
├── test_podcast_generation.py
├── auth/
│   └── test_provider.py
└── utils/
    └── test_vertex_client.py
```
