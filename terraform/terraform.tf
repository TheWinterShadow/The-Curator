terraform {
  cloud {
    organization = "TheWinterShadow" # Replace with your HCP Terraform org name before running terraform init

    workspaces {
      name = "the-curator"
    }
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10.0"
    }
  }

  required_version = ">= 1.2"
}