# ClipVault Public API

FastAPI-based public API for ClipVault MVP - providing link ingestion, search, and collections functionality with automatic cloud deployment on Google Cloud Run.

## Features

- **Link Ingestion**: Save and process links with AI-powered content extraction
- **Full-Text Search**: Search across transcripts and summaries using PostgreSQL FTS
- **Collections**: Organize clips into user-defined collections
- **Authentication**: Supabase-based OAuth with JWT tokens
- **Real-time Processing**: Event-driven architecture with Cloud Pub/Sub
- **Cloud Native**: Deployed on Google Cloud Run with auto-scaling (0-20 instances)
- **Automatic Deployment**: Google Cloud Build automatically deploys on repository pushes

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Cloud Run      │    │   Supabase      │
│   (Repository)  │───▶│   (FastAPI)      │───▶│   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│  Cloud Build    │    │   Pub/Sub        │
│  (Auto Deploy)  │    │   (Events)       │
└─────────────────┘    └──────────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Poetry** (for dependency management)
- **Docker & Docker Compose** (for local development)
- **Google Cloud Project** (for deployment)

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

### Automatic Deployment Setup

The repository is configured for **automatic deployment** to Google Cloud Run using Google Cloud Build.

#### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Required APIs enabled**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

3. **Create a service account** for Cloud Run:
   ```bash
   gcloud iam service-accounts create clipvault-api-staging \
     --display-name="ClipVault API Staging"
   ```

4. **Set up Cloud Build trigger**:
   - Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
   - Connect your GitHub repository
   - Create trigger for `main` branch pushes
   - Point to `cloudbuild.yaml` file

#### Deployment Process

1. **Push to main branch** - triggers automatic deployment
2. **Cloud Build** builds Docker image from `docker/Dockerfile`
3. **Image pushed** to Google Container Registry
4. **Cloud Run service** automatically updated with new image

### Manual Docker Build

To test the production Docker image locally:

```bash
# Build the production image
docker build -f docker/Dockerfile -t clipvault-api .

# Run the container
docker run -p 8000:8000 clipvault-api

# Test the deployment
curl http://localhost:8000/ping
```

### Cloud Run Configuration

The service is configured with:
- **Auto-scaling**: 0-20 instances
- **Memory**: 512Mi per instance  
- **CPU**: 1 vCPU per instance
- **Port**: 8000
- **Health checks**: `/ping` endpoint
- **Public access**: Unauthenticated requests allowed

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

For sensitive environment variables, use Google Cloud Secret Manager:

```bash
# Create secrets
gcloud secrets create supabase-url --data-file=-
gcloud secrets create supabase-anon-key --data-file=-
gcloud secrets create supabase-service-role-key --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding supabase-url \
  --member="serviceAccount:clipvault-api-staging@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Project Structure

```
ClipVault-PublicAPI/
├── api/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   └── (routes, services, etc. - coming soon)
├── tests/                 # Test suite
├── docker/                # Docker configuration
│   ├── Dockerfile         # Production container
│   └── Dockerfile.dev     # Development container
├── cloudbuild.yaml        # Google Cloud Build configuration
├── docker-compose.yml     # Development environment
├── pyproject.toml         # Poetry configuration
└── README.md             # This file
```

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Make changes and test locally**
3. **Run tests**: `poetry run pytest`
4. **Create pull request**: Review changes
5. **Merge to main**: Triggers automatic deployment to staging

## Monitoring

- **Cloud Run Logs**: Available in Google Cloud Console
- **Health Check**: `/ping` endpoint returns `{"pong": true}`
- **API Documentation**: Available at `/docs` when service is running
- **Metrics**: Built-in Cloud Run metrics for requests, latency, errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Security

- **Non-root container**: App runs as non-root user
- **Minimal attack surface**: Multi-stage Docker build
- **Dependency scanning**: Keep dependencies updated
- **HTTPS**: Cloud Run provides automatic TLS termination

## Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Available at `/docs` endpoint when running
- **Monitoring**: Cloud Run logs and metrics in GCP Console

## License

MIT License - see LICENSE file for details. 