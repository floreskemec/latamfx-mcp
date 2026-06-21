variable "project_id" {
  type        = string
  description = "GCP project ID to deploy into."
}

variable "region" {
  type        = string
  description = "GCP region for Cloud Run."
  default     = "southamerica-east1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name."
  default     = "latamfx-mcp"
}

variable "image" {
  type        = string
  description = "Fully-qualified container image, e.g. REGION-docker.pkg.dev/PROJECT/REPO/latamfx-mcp:TAG."
}

variable "max_instances" {
  type        = number
  description = "Maximum Cloud Run instances."
  default     = 3
}

variable "cache_ttl_seconds" {
  type        = number
  description = "TTL for the in-process FX cache."
  default     = 60
}

variable "allow_unauthenticated" {
  type        = bool
  description = "If true, grant run.invoker to allUsers. Keep false in real deployments."
  default     = false
}

output "service_uri" {
  description = "The deployed Cloud Run service URL."
  value       = google_cloud_run_v2_service.latamfx_mcp.uri
}
