---
title: Terraform
icon: simple/terraform
---

# Terraform

All GCP infrastructure is defined in `terraform/main.tf`. The Terraform Cloud workspace handles remote state.

## First-time setup

### 1. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project=the-curator-496412
```

### 2. Create a Terraform Cloud workspace

Create a workspace in [app.terraform.io](https://app.terraform.io) and set the `TF_API_TOKEN` GitHub secret.

### 3. Create an Artifact Registry repository

```bash
gcloud artifacts repositories create the-curator \
  --repository-format=docker \
  --location=us-central1 \
  --project=the-curator-496412
```

### 4. Configure GitHub secrets

| Secret | Description |
| --- | --- |
| `GCP_SA_KEY` | Service account key JSON with `roles/run.admin`, `roles/storage.admin`, `roles/secretmanager.admin`, `roles/artifactregistry.writer`, `roles/iam.serviceAccountAdmin`, `roles/resourcemanager.projectIamAdmin` |
| `GCP_PROJECT_ID` | `the-curator-496412` |
| `TF_API_TOKEN` | Terraform Cloud API token |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `ALLOWED_EMAIL` | Authorized Google account email |
| `SERVER_URL` | Cloud Run service URL (after first deploy) |

### 5. Push to main

The Deploy workflow runs `terraform apply` automatically. The first apply creates all resources. Subsequent deploys update the Cloud Run image.

## Manual apply

```bash
cd terraform
terraform init
terraform apply \
  -var="podcast_service_image_uri=us-central1-docker.pkg.dev/the-curator-496412/the-curator/the-curator-bot:latest" \
  -var="google_client_id=..." \
  -var="google_client_secret=..." \
  -var="allowed_email=you@example.com" \
  -var="server_url=https://your-cloud-run-url"
```

## Resources reference

### Cloud Run service

```hcl
resource "google_cloud_run_v2_service" "podcast_service" {
  name     = "podcast-service"
  location = "us-central1"
  ingress  = "INGRESS_TRAFFIC_ALL"
  ...
}
```

The service is public (`allUsers` can invoke it) so that `mcp-remote` and MCP clients can reach the OAuth discovery endpoints without authentication. The MCP tools themselves require a valid OAuth token.

### GCS buckets

| Bucket | Access | Purpose |
| --- | --- | --- |
| `the-curator-podcast-data` | Public read | Episode audio |
| `the-curator-oauth-state` | Private (SA only) | OAuth state JSON |

### Secret Manager

Secrets `google-client-id`, `google-client-secret`, and `allowed-email` are created by Terraform and populated from `var.*`. They are injected into the Cloud Run container as environment variables via `secretKeyRef`.
