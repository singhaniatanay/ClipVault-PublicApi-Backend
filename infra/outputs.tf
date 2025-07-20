output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.api_service.uri
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.api_service.name
}

output "service_account_email" {
  description = "Email of the service account used by Cloud Run"
  value       = google_service_account.cloudrun_sa.email
}

output "artifact_registry_url" {
  description = "URL of the Artifact Registry repository"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.container_repo.repository_id}"
}

output "pubsub_topic_name" {
  description = "Name of the Pub/Sub topic"
  value       = google_pubsub_topic.clip_events.name
}

output "secret_names" {
  description = "Names of created secrets in Secret Manager"
  value = {
    supabase_url              = google_secret_manager_secret.supabase_url.secret_id
    supabase_anon_key         = google_secret_manager_secret.supabase_anon_key.secret_id
    supabase_service_role_key = google_secret_manager_secret.supabase_service_role_key.secret_id
    redis_url                 = var.redis_url != "" ? google_secret_manager_secret.redis_url[0].secret_id : null
  }
} 