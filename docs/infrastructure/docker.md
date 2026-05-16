---
title: Docker
icon: fontawesome/brands/docker
---

# Docker

## Image

The Dockerfile uses a standard Python slim base, installs dependencies from `pyproject.toml` via Hatch, and starts the server with Gunicorn + Uvicorn workers.

The image is built and pushed to Google Artifact Registry by the [Deploy workflow](https://github.com/TheWinterShadow/The-Curator/actions/workflows/deploy.yml):

```
us-central1-docker.pkg.dev/<PROJECT_ID>/the-curator/the-curator-bot:<sha>
us-central1-docker.pkg.dev/<PROJECT_ID>/the-curator/the-curator-bot:latest
```

## Build locally

```bash
docker build -t the-curator .
```

## Run locally

```bash
docker run --rm -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=your-client-id \
  -e GOOGLE_CLIENT_SECRET=your-client-secret \
  -e ALLOWED_EMAIL=you@example.com \
  -e SERVER_URL=http://localhost:8080 \
  the-curator
```

The SSE endpoint is at `http://localhost:8080/sse`. Point an MCP client at it.

## GCS access locally

The container needs GCP credentials to access Cloud Storage (OAuth state and episode uploads). Mount ADC credentials:

```bash
docker run --rm -p 8080:8080 \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  -e GOOGLE_CLIENT_ID=... \
  -e GOOGLE_CLIENT_SECRET=... \
  -e ALLOWED_EMAIL=... \
  -e SERVER_URL=http://localhost:8080 \
  the-curator
```

## Cloud Run specifics

- The service is deployed in `us-central1` with `INGRESS_TRAFFIC_ALL` to allow public access.
- The service account identity grants all needed IAM permissions; no service account key is mounted.
- Cloud Run injects secrets from Secret Manager at container startup via `secretKeyRef` environment variables.
- Port `8080` is the Cloud Run default and matches the Uvicorn startup command.
