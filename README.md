# ClipVault Public API

FastAPI-based public API for ClipVault MVP - providing link ingestion, search, and collections functionality.

## Features

- **Link Ingestion**: Save and process links with AI-powered content extraction
- **Full-Text Search**: Search across transcripts and summaries using PostgreSQL FTS
- **Collections**: Organize clips into user-defined collections
- **Authentication**: Supabase-based OAuth with JWT tokens
- **Real-time Processing**: Event-driven architecture with Cloud Pub/Sub

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry (for dependency management)
- Docker & Docker Compose (for development)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ClipVault-PublicAPI
   ```

2. **Install dependencies with Poetry**:
   ```bash
   poetry install
   ```

3. **Run the application**:
   ```bash
   poetry run python -m api.main
   ```
   
   Or using uvicorn directly:
   ```bash
   poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Test the health endpoint**:
   ```bash
   curl http://localhost:8000/ping
   # Expected response: {"pong": true}
   ```

### Docker Development

1. **Build and run with docker-compose**:
   ```bash
   docker-compose up --build
   ```

2. **Test the health endpoint**:
   ```bash
   curl http://localhost:8000/ping
   # Expected response: {"pong": true}
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f api
   ```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

### Code Quality

This project uses several tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Black**: Code formatting
- **isort**: Import sorting

Run quality checks:
```bash
# Lint with Ruff
poetry run ruff check .

# Type check with MyPy
poetry run mypy .

# Format code
poetry run black .
poetry run isort .
```

### Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=api
```

## Project Structure

```
ClipVault-PublicAPI/
├── api/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── routes/            # API route handlers
│   ├── services/          # Business logic services
│   ├── schemas/           # Pydantic models
│   └── middleware/        # Custom middleware
├── tests/                 # Test suite
├── docker/                # Docker configuration
│   └── Dockerfile.dev     # Development Dockerfile
├── docker-compose.yml     # Development environment
├── pyproject.toml         # Poetry configuration
└── README.md             # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `development` |
| `LOG_LEVEL` | Logging level | `info` |
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `SUPABASE_URL` | Supabase project URL | - |
| `SUPABASE_KEY` | Supabase anon key | - |

## Architecture

The ClipVault Public API follows a clean architecture pattern:

- **FastAPI**: Modern, fast web framework for APIs
- **Supabase**: Backend-as-a-Service for auth and database
- **PostgreSQL**: Primary database with full-text search
- **Redis**: Caching and session storage
- **Cloud Pub/Sub**: Event-driven processing
- **Cloud Run**: Serverless deployment platform

## Contributing

1. Install development dependencies: `poetry install`
2. Run quality checks before committing
3. Write tests for new features
4. Update documentation as needed

## License

[License details to be added] 