# ClipVault Public API

**ClipVault Public API** - FastAPI service for link ingestion, search, and collections.

## Quick Start

### Prerequisites
- Python 3.12+
- Poetry
- Supabase project

### Environment Setup

1. **Create environment file**:
   ```bash
   cp .env.example .env  # If .env.example exists, or create .env manually
   ```

2. **Configure Supabase variables** in `.env`:
   ```bash
   # General Settings
   ENVIRONMENT=development
   LOG_LEVEL=info
   PORT=8000

   # Supabase Configuration
   # Get these from your Supabase project dashboard: Settings -> API
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your_supabase_anon_key_here
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
   SUPABASE_JWT_SECRET=your_supabase_jwt_secret_here

   # Optional - for future features
   REDIS_URL=redis://localhost:6379/0
   GOOGLE_CLOUD_PROJECT=your_gcp_project_id
   PUBSUB_TOPIC_CLIP_CREATED=clip-created
   ```

3. **Get Supabase credentials**:
   - Go to your Supabase project dashboard
   - Navigate to **Settings** → **API**
   - Copy the **Project URL** (SUPABASE_URL)
   - Copy the **anon public** key (SUPABASE_ANON_KEY)
   - Copy the **service_role** key (SUPABASE_SERVICE_ROLE_KEY)
   - Navigate to **Settings** → **API** → **JWT Settings**
   - Copy the **JWT Secret** (SUPABASE_JWT_SECRET)
   - Navigate to **Settings** → **Database** → **Connection pooling**
   - Copy the **Password** (SUPABASE_DB_PASSWORD)

### 🔄 CI/CD & Database Setup

For automated database migrations via GitHub Actions:

1. **Configure GitHub Secrets**: `SUPABASE_URL` and `SUPABASE_DB_PASSWORD`
2. **Deploy Database**: Run `cd db && ./deploy.sh`

### Installation & Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run python -m api.main

# Or using uvicorn directly
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run auth tests specifically
poetry run pytest tests/test_auth.py -v

# Run with coverage
poetry run pytest --cov=api tests/
```

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/ping
```

#### Authentication
```bash
# Test /me endpoint (requires valid JWT token)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/auth/me

# Verify token
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/auth/verify
```

#### Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

This API uses **Supabase JWT tokens** for authentication. Protected endpoints require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

### Getting a JWT Token

Currently, the OAuth token exchange endpoint (`POST /auth/token`) is not fully implemented. For testing, you can:

1. **Generate test tokens** using your Supabase JWT secret
2. **Use Supabase client libraries** in your frontend to get tokens
3. **Use Supabase Auth UI** for development

### Supported Endpoints

- `POST /auth/token` - OAuth code exchange (placeholder)
- `GET /auth/me` - Get current user profile
- `GET /auth/verify` - Verify token validity

## Project Structure

```
api/
├── main.py           # FastAPI application
├── routes/
│   └── auth.py       # Authentication routes
├── services/
│   └── auth.py       # Authentication service & JWT validation
└── schemas/
    └── auth.py       # Pydantic models for auth

tests/
└── test_auth.py      # Authentication tests
```

## Task Status

✅ **API-AUTH-003**: Supabase Auth middleware - COMPLETED
- [x] JWKS fetching and caching
- [x] JWT verification with PyJWT
- [x] FastAPI dependency `get_current_user()`
- [x] 401/403 exception handlers
- [x] `/me` endpoint returning 401 without token
- [x] Comprehensive test suite

## Next Steps

- **API-DB-004**: Supabase Postgres wrapper
- **API-ROUTE-006**: `/auth/token` endpoint implementation
- **API-ROUTE-008**: `/clips` POST endpoint

## Docker Development

```bash
# Build and run with docker-compose
docker-compose up --build

# API will be available at http://localhost:8000
```

## Production Deployment

This API is designed for deployment on **Google Cloud Run**. See the `docker/` and infrastructure configuration for deployment details.

---

For more details, see the [LLD Public API](.context/LLD%20Public%20API.md) and [Task Breakdown](.context/Task%20Breakdown%20for%20Public%20API.md) documents. 