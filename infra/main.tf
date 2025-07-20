# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Service Account for Cloud Run
resource "google_service_account" "cloudrun_sa" {
  account_id   = "${var.service_name}-${var.environment}"
  display_name = "Cloud Run Service Account for ${var.service_name} (${var.environment})"
  description  = "Service account used by Cloud Run service ${var.service_name} in ${var.environment}"
  
  depends_on = [google_project_service.required_apis]
}

# IAM roles for the service account
resource "google_project_iam_member" "cloudrun_sa_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/cloudsql.client"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
}

# Secret Manager secrets for sensitive configuration
resource "google_secret_manager_secret" "supabase_url" {
  secret_id = "${var.service_name}-${var.environment}-supabase-url"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "supabase_url" {
  secret      = google_secret_manager_secret.supabase_url.id
  secret_data = var.supabase_url
}

resource "google_secret_manager_secret" "supabase_anon_key" {
  secret_id = "${var.service_name}-${var.environment}-supabase-anon-key"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "supabase_anon_key" {
  secret      = google_secret_manager_secret.supabase_anon_key.id
  secret_data = var.supabase_anon_key
}

resource "google_secret_manager_secret" "supabase_service_role_key" {
  secret_id = "${var.service_name}-${var.environment}-supabase-service-role-key"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "supabase_service_role_key" {
  secret      = google_secret_manager_secret.supabase_service_role_key.id
  secret_data = var.supabase_service_role_key
}

# Redis URL secret (optional)
resource "google_secret_manager_secret" "redis_url" {
  count     = var.redis_url != "" ? 1 : 0
  secret_id = "${var.service_name}-${var.environment}-redis-url"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "redis_url" {
  count       = var.redis_url != "" ? 1 : 0
  secret      = google_secret_manager_secret.redis_url[0].id
  secret_data = var.redis_url
}

# Pub/Sub topic for events
resource "google_pubsub_topic" "clip_events" {
  name = var.pubsub_topic_name
  
  depends_on = [google_project_service.required_apis]
}

# Artifact Registry repository for container images
resource "google_artifact_registry_repository" "container_repo" {
  location      = var.region
  repository_id = "${var.service_name}-${var.environment}"
  description   = "Container repository for ${var.service_name} (${var.environment})"
  format        = "DOCKER"
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Run service
resource "google_cloud_run_v2_service" "api_service" {
  name     = "${var.service_name}-${var.environment}"
  location = var.region
  
  deletion_protection = false
  
  template {
    service_account = google_service_account.cloudrun_sa.email
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    containers {
      image = var.container_image
      
      ports {
        container_port = var.port
        name          = "http1"
      }
      
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      
      env {
        name  = "PORT"
        value = tostring(var.port)
      }
      
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      
      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_url.secret_id
            version = "latest"
          }
        }
      }
      
      env {
        name = "SUPABASE_ANON_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_anon_key.secret_id
            version = "latest"
          }
        }
      }
      
      env {
        name = "SUPABASE_SERVICE_ROLE_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_service_role_key.secret_id
            version = "latest"
          }
        }
      }
      
      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.clip_events.name
      }
      
      dynamic "env" {
        for_each = var.redis_url != "" ? [1] : []
        content {
          name = "REDIS_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.redis_url[0].secret_id
              version = "latest"
            }
          }
        }
      }
      
      startup_probe {
        http_get {
          path = "/ping"
          port = var.port
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }
      
      liveness_probe {
        http_get {
          path = "/ping"
          port = var.port
        }
        initial_delay_seconds = 30
        timeout_seconds       = 5
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
  }
  
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_project_iam_member.cloudrun_sa_roles
  ]
}

# Allow unauthenticated invocations to Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.api_service.location
  service  = google_cloud_run_v2_service.api_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
} 