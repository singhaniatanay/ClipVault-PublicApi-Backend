# ClipVault Public API

FastAPI-based public API for ClipVault MVP - providing link ingestion, search, and collections functionality with cloud deployment on Google Cloud Run.

## Features

- **Link Ingestion**: Save and process links with AI-powered content extraction
- **Full-Text Search**: Search across transcripts and summaries using PostgreSQL FTS
- **Collections**: Organize clips into user-defined collections
- **Authentication**: Supabase-based OAuth with JWT tokens
- **Real-time Processing**: Event-driven architecture with Cloud Pub/Sub
- **Cloud Native**: Deployed on Google Cloud Run with auto-scaling (0-20 instances)
- **Infrastructure as Code**: Terraform-managed infrastructure
- **CI/CD Pipeline**: Automated testing, building, and deployment via GitHub Actions

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Cloud Run      │    │   Supabase      │
│   (CI/CD)       │───▶│   (FastAPI)      │───▶│   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Pub/Sub        │
                       │   (Events)       │
                       └──────────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Poetry** (for dependency management)
- **Docker & Docker Compose** (for local development)
- **Google Cloud SDK** (for cloud deployment)
- **Terraform 1.6+** (for infrastructure management)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/singhaniatanay/ClipVault-PublicApi-Backend.git
   cd ClipVault-PublicAPI
   ```

2. **Install dependencies with Poetry**:
   ```bash
   poetry install
   ```

3. **Run locally with Poetry**:
   ```bash
   poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Or use Docker Compose for full environment**:
   ```bash
   docker-compose up
   ```

5. **Test the API**:
   ```bash
   curl http://localhost:8000/ping
   # Should return: {"pong": true}
   ```

6. **View API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=api --cov-report=html

# Run linting
poetry run ruff check .
poetry run ruff format .

# Run type checking
poetry run mypy .
```

## Cloud Deployment

### Prerequisites for Deployment

1. **Google Cloud Project** with billing enabled
2. **Required APIs enabled**:
   - Cloud Run API
   - Secret Manager API
   - Pub/Sub API
   - Cloud Build API
   - Artifact Registry API

3. **Required secrets** (for GitHub Actions):
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `WIF_PROVIDER`: Workload Identity Federation provider
   - `WIF_SERVICE_ACCOUNT`: Service account for deployment
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_ANON_KEY`: Supabase anonymous key
   - `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
   - `REDIS_URL`: Redis connection URL (optional)

### Manual Deployment

1. **Configure Terraform variables**:
   ```bash
   cd infra
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Deploy using the script**:
   ```bash
   ./scripts/deploy.sh staging your-gcp-project-id
   ```

3. **Or deploy manually**:
   ```bash
   # Build and push container
   docker build -f docker/Dockerfile -t gcr.io/your-project/clipvault-api .
   docker push gcr.io/your-project/clipvault-api
   
   # Deploy infrastructure
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```

### Automated Deployment (CI/CD)

The project includes a complete CI/CD pipeline via GitHub Actions:

**On Pull Requests**:
- ✅ Run tests and linting
- ✅ Type checking with MyPy
- ✅ Security scanning with Trivy
- ✅ Code coverage reporting

**On Main Branch Push**:
- ✅ All PR checks
- ✅ Build Docker image
- ✅ Push to Artifact Registry
- ✅ Deploy to Cloud Run via Terraform
- ✅ Health check verification
- ✅ Deployment notification

### Infrastructure

The Terraform configuration creates:

- **Cloud Run service** with auto-scaling (0-20 instances)
- **Service Account** with minimal required permissions
- **Secret Manager secrets** for sensitive configuration
- **Pub/Sub topic** for event publishing
- **Artifact Registry repository** for container images
- **IAM policies** for secure access

### Monitoring and Observability

- **Health checks**: `/ping` endpoint for service health
- **Structured logging**: JSON-formatted logs with correlation IDs
- **Cloud Run metrics**: Built-in CPU, memory, and request metrics
- **Error tracking**: Automatic error reporting to Cloud Logging

## API Endpoints

### Health & Status
- `GET /ping` - Health check endpoint
- `GET /` - API information and links

### Authentication (Coming Soon)
- `POST /auth/token` - Exchange OAuth code for JWT
- `GET /me` - Get authenticated user profile

### Clips (Coming Soon)
- `POST /clips` - Save a new link
- `GET /clips/{id}` - Get clip details
- `GET /search` - Search clips by keyword/tags

### Collections (Coming Soon)
- `GET /collections` - List user collections
- `POST /collections` - Create new collection
- `PATCH /collections/{id}` - Update collection

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ENVIRONMENT` | Environment name | No | `development` |
| `PORT` | Server port | No | `8000` |
| `PROJECT_ID` | GCP project ID | Yes | - |
| `SUPABASE_URL` | Supabase project URL | Yes | - |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes | - |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes | - |
| `REDIS_URL` | Redis connection URL | No | - |
| `PUBSUB_TOPIC` | Pub/Sub topic name | No | `clip-events` |

### Secret Management

Sensitive configuration is stored in Google Cloud Secret Manager:
- Database credentials
- API keys
- Service account keys

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Make changes and test locally**
3. **Run tests**: `poetry run pytest`
4. **Create pull request**: Triggers CI pipeline
5. **Merge to main**: Triggers deployment to staging
6. **Promote to production**: Manual Terraform deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Security

- **Non-root container**: App runs as non-root user
- **Minimal permissions**: Service account with least-privilege access
- **Secret management**: All sensitive data in Secret Manager
- **Network security**: Cloud Run with VPC connector (optional)
- **Dependency scanning**: Automated vulnerability scanning

## Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Available at `/docs` endpoint when running
- **Monitoring**: Cloud Run logs and metrics in GCP Console

## License

MIT License - see LICENSE file for details. 