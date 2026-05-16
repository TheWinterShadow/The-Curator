---
title: Configuration
icon: material/tune
---

# Configuration

The Curator is configured entirely through environment variables. There are no config files — all values are injected at runtime by Cloud Run from Secret Manager and plain environment variables.

## Required variables

| Variable | Description |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 client ID. Create at [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials). Stored in Secret Manager. |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 2.0 client secret. Stored in Secret Manager. |
| `ALLOWED_EMAIL` | The single Google account email authorized to use the server. Stored in Secret Manager. |
| `SERVER_URL` | The public HTTPS base URL of the server, no trailing slash. Used to construct OAuth redirect URIs and discovery endpoints. |

## Optional variables

| Variable | Default | Description |
| --- | --- | --- |
| `GCS_BUCKET_NAME` | `the-curator-podcast-data` | GCS bucket where episode `.wav` files are uploaded. |
| `OAUTH_STATE_BUCKET` | `the-curator-oauth-state` | Private GCS bucket for OAuth state persistence. |
| `GOOGLE_CLOUD_PROJECT` | `the-curator` | GCP project ID, used by `PodcastGeneration` to initialize the Vertex AI client. |
| `PORT` | `8000` | Port Uvicorn listens on (set by Cloud Run automatically). |

## OAuth token lifetimes

These are hardcoded in [`auth/provider.py`](../api/auth/provider.md) and not configurable at runtime:

| Token | Lifetime |
| --- | --- |
| Access token | 1 hour |
| Refresh token | 30 days |
| Authorization code | 5 minutes |
| Pending auth state | 10 minutes |

## Cloud Run environment

In production, secrets are injected from Secret Manager via `valueSource.secretKeyRef` in the Terraform config — they are never stored as plain environment variables in the container image or Cloud Run service definition. See [Infrastructure → Terraform](../infrastructure/terraform.md).

## Local development

For local development, export variables in your shell or use a `.env` loader:

```bash
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
export ALLOWED_EMAIL="you@example.com"
export SERVER_URL="http://localhost:8000"
hatch run start
```

!!! warning "GCS access"
    The server connects to GCS for both OAuth state and episode uploads. Locally, ensure you are authenticated with Application Default Credentials:

    ```bash
    gcloud auth application-default login
    ```
