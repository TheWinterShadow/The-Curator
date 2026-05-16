---
title: Installation
icon: material/download
---

# Installation

## Requirements

| Requirement | Version |
| --- | --- |
| Python | 3.11+ |
| Hatch | latest |
| Docker | 24+ (optional) |
| GCP project | billing enabled |

## Local setup

Install [Hatch](https://hatch.pypa.io/latest/install/):

```bash
pipx install hatch
```

Clone the repo and install dependencies:

```bash
git clone https://github.com/TheWinterShadow/The-Curator.git
cd The-Curator
hatch env create
```

Hatch reads `pyproject.toml` and creates an isolated virtualenv with all dependencies.

## Environment variables

Create a `.env` file or export these in your shell:

```bash
# Required
export GOOGLE_CLIENT_ID="your-google-oauth-client-id"
export GOOGLE_CLIENT_SECRET="your-google-oauth-client-secret"
export ALLOWED_EMAIL="you@example.com"
export SERVER_URL="http://localhost:8000"

# Optional — defaults shown
export GCS_BUCKET_NAME="the-curator-podcast-data"
export OAUTH_STATE_BUCKET="the-curator-oauth-state"
export GOOGLE_CLOUD_PROJECT="the-curator"
```

See [Configuration](../configuration/index.md) for the full variable reference.

## Run the server

```bash
hatch run start
```

The server starts on `http://localhost:8000`. The SSE endpoint is at `/sse`.

## Run checks

```bash
hatch run check   # lint + typecheck + tests
hatch run test    # tests only
hatch run lint    # ruff only
```

## Docker

Build and run with Docker instead of Hatch:

```bash
docker build -t the-curator .

docker run --rm -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=... \
  -e GOOGLE_CLIENT_SECRET=... \
  -e ALLOWED_EMAIL=you@example.com \
  -e SERVER_URL=http://localhost:8080 \
  the-curator
```

!!! note "GCS access in local Docker"
    When running locally, the container won't have access to GCS unless you mount Application Default Credentials:

    ```bash
    docker run --rm -p 8080:8080 \
      -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
      -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
      -e GOOGLE_CLIENT_ID=... \
      ... \
      the-curator
    ```
