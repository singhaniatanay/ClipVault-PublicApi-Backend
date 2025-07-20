#!/bin/bash

# ClipVault Public API Deployment Script
# Usage: ./scripts/deploy.sh [environment] [project_id]

set -e  # Exit on any error

# Configuration
ENVIRONMENT=${1:-staging}
PROJECT_ID=${2:-}
SERVICE_NAME="clipvault-public-api"
REGION="us-central1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if project ID is provided
if [ -z "$PROJECT_ID" ]; then
    log_error "Project ID is required"
    echo "Usage: $0 [environment] [project_id]"
    echo "Example: $0 staging my-gcp-project"
    exit 1
fi

log_info "Starting deployment for environment: $ENVIRONMENT"
log_info "Project ID: $PROJECT_ID"
log_info "Service: $SERVICE_NAME"
log_info "Region: $REGION"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
    exit 1
fi

# Set the project
log_info "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Build and push container
log_info "Building Docker image..."
REPO_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}-${ENVIRONMENT}"
IMAGE_TAG="${REPO_URL}/${SERVICE_NAME}:$(git rev-parse --short HEAD)"
IMAGE_LATEST="${REPO_URL}/${SERVICE_NAME}:latest"

# Configure Docker for Artifact Registry
log_info "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build the image
log_info "Building container image..."
docker build -f docker/Dockerfile -t $IMAGE_TAG -t $IMAGE_LATEST .

# Push the image
log_info "Pushing container image..."
docker push $IMAGE_TAG
docker push $IMAGE_LATEST

# Deploy with Terraform
log_info "Deploying infrastructure with Terraform..."
cd infra

# Check if terraform.tfvars exists
if [ ! -f terraform.tfvars ]; then
    log_warn "terraform.tfvars not found. Please create it from terraform.tfvars.example"
    log_info "You can copy the example: cp terraform.tfvars.example terraform.tfvars"
    exit 1
fi

# Initialize Terraform
log_info "Initializing Terraform..."
terraform init

# Plan the deployment
log_info "Planning Terraform deployment..."
terraform plan \
    -var="project_id=$PROJECT_ID" \
    -var="environment=$ENVIRONMENT" \
    -var="container_image=$IMAGE_TAG" \
    -out=tfplan

# Ask for confirmation
echo
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Deployment cancelled"
    exit 0
fi

# Apply the deployment
log_info "Applying Terraform deployment..."
terraform apply -auto-approve tfplan

# Get the service URL
SERVICE_URL=$(terraform output -raw service_url)
log_info "Service deployed to: $SERVICE_URL"

# Test the deployment
log_info "Testing deployment..."
sleep 10  # Wait for service to be ready

if curl -f "${SERVICE_URL}/ping" >/dev/null 2>&1; then
    log_info "✅ Deployment successful! Service is responding."
    echo
    echo "🚀 Service URL: $SERVICE_URL"
    echo "📊 Health Check: ${SERVICE_URL}/ping"
    echo "📖 API Docs: ${SERVICE_URL}/docs"
else
    log_error "❌ Deployment failed! Service is not responding."
    exit 1
fi

log_info "Deployment complete!" 