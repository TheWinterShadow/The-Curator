
provider "google" {
  project = "the-curator-496412"
  region  = "us-central1"
  zone    = "us-central1-c"
}


// Variables
variable "podcast_service_image_uri" {
  description = "Container image URI for the Cloud Run service."
  type        = string
}

variable "google_client_id" {
  description = "Google OAuth 2.0 Client ID for MCP authentication."
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth 2.0 Client Secret for MCP authentication."
  type        = string
  sensitive   = true
}

variable "allowed_email" {
  description = "Google account email address authorized to use the MCP server."
  type        = string
  sensitive   = true
}

variable "server_url" {
  description = "Public HTTPS URL of the Cloud Run service (no trailing slash)."
  type        = string
}


// Enable Secret Manager API
resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}


// Service account for the Cloud Run service
resource "google_service_account" "podcast_service" {
  account_id   = "podcast-service"
  display_name = "The Curator Cloud Run SA"
}

// Grant the SA access to GCS for episode uploads and OAuth state
resource "google_storage_bucket_iam_member" "podcast_service_storage" {
  depends_on = [google_service_account.podcast_service]
  bucket     = google_storage_bucket.podcast_data.name
  role       = "roles/storage.objectAdmin"
  member     = "serviceAccount:${google_service_account.podcast_service.email}"
}

// Grant the SA access to Vertex AI (Gemini TTS + transcript generation)
resource "google_project_iam_member" "podcast_service_aiplatform" {
  depends_on = [google_service_account.podcast_service]
  project    = "the-curator-496412"
  role       = "roles/aiplatform.user"
  member     = "serviceAccount:${google_service_account.podcast_service.email}"
}


// Secret Manager secrets for OAuth credentials
resource "google_secret_manager_secret" "google_client_id" {
  secret_id  = "google-client-id"
  depends_on = [google_project_service.secretmanager]

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_client_id" {
  secret      = google_secret_manager_secret.google_client_id.id
  secret_data = var.google_client_id
}

resource "google_secret_manager_secret_iam_member" "google_client_id_accessor" {
  secret_id = google_secret_manager_secret.google_client_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.podcast_service.email}"
}

resource "google_secret_manager_secret" "google_client_secret" {
  secret_id  = "google-client-secret"
  depends_on = [google_project_service.secretmanager]

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_client_secret" {
  secret      = google_secret_manager_secret.google_client_secret.id
  secret_data = var.google_client_secret
}

resource "google_secret_manager_secret_iam_member" "google_client_secret_accessor" {
  secret_id = google_secret_manager_secret.google_client_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.podcast_service.email}"
}

resource "google_secret_manager_secret" "allowed_email" {
  secret_id  = "allowed-email"
  depends_on = [google_project_service.secretmanager]

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "allowed_email" {
  secret      = google_secret_manager_secret.allowed_email.id
  secret_data = var.allowed_email
}

resource "google_secret_manager_secret_iam_member" "allowed_email_accessor" {
  secret_id = google_secret_manager_secret.allowed_email.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.podcast_service.email}"
}


// Public bucket for episode audio files
resource "google_storage_bucket" "podcast_data" {
  name          = "the-curator-podcast-data"
  location      = "US"
  force_destroy = true
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.podcast_data.name
  role   = "READER"
  entity = "allUsers"
}

// Private bucket for OAuth state (tokens must not be publicly accessible)
resource "google_storage_bucket" "oauth_state" {
  name                        = "the-curator-oauth-state"
  location                    = "US"
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "podcast_service_oauth_storage" {
  depends_on = [google_service_account.podcast_service]
  bucket     = google_storage_bucket.oauth_state.name
  role       = "roles/storage.objectAdmin"
  member     = "serviceAccount:${google_service_account.podcast_service.email}"
}

// Allow unauthenticated invocations so mcp-remote can reach OAuth discovery endpoints
resource "google_cloud_run_v2_service_iam_member" "noauth" {
  name     = google_cloud_run_v2_service.podcast_service.name
  location = google_cloud_run_v2_service.podcast_service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

// Google Cloud Run Service
resource "google_cloud_run_v2_service" "podcast_service" {
  name     = "podcast-service"
  location = "us-central1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.podcast_service.email

    containers {
      image = var.podcast_service_image_uri

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = "the-curator-496412"
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.podcast_data.name
      }

      env {
        name  = "OAUTH_STATE_BUCKET"
        value = google_storage_bucket.oauth_state.name
      }

      env {
        name  = "SERVER_URL"
        value = var.server_url
      }

      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_id.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ALLOWED_EMAIL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.allowed_email.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.google_client_id_accessor,
    google_secret_manager_secret_iam_member.google_client_secret_accessor,
    google_secret_manager_secret_iam_member.allowed_email_accessor,
  ]
}
