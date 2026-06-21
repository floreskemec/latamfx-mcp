terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Run service running the MCP server over a streamable HTTP transport.
# (stdio is used locally; for a hosted deployment expose HTTP and front it with
# auth/IAP as appropriate for your environment.)
resource "google_cloud_run_v2_service" "latamfx_mcp" {
  name     = var.service_name
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "LATAMFX_CACHE_TTL"
        value = tostring(var.cache_ttl_seconds)
      }
    }
  }
}

# Optionally allow unauthenticated access (disabled by default).
resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_unauthenticated ? 1 : 0
  name     = google_cloud_run_v2_service.latamfx_mcp.name
  location = google_cloud_run_v2_service.latamfx_mcp.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
