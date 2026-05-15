
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


// Google Cloud Storage bucket for storing conversation data
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

// Google Cloud Run Service for hosting the podcast MCP
resource "google_cloud_run_v2_service" "podcast_service" {
  name     = "podcast_service"
  location = "us-central1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.podcast_service_image_uri
      ports {
        container_port = 8080
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.podcast_data.name
      }
    }
  }
}