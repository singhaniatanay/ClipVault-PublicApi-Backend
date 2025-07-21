# ClipVault Public API

**ClipVault Public API** - FastAPI service for link ingestion, search, and collections with Supabase authentication and database integration.

## ✨ Key Features

- 🔐 **Supabase Authentication**: Complete Google OAuth integration with JWT token exchange
- 🗄️ **Database Integration**: PostgreSQL with connection pooling and Row Level Security  
- 🚀 **Auto-Migrations**: Sqitch-based database migrations with GitHub Actions CI/CD
- 🧪 **Interactive Testing**: HTML test page for OAuth flow validation
- 📊 **Health Monitoring**: Comprehensive health checks for all services
- 🔒 **Security**: JWT verification, RLS policies, and proper error handling

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
   SUPABASE_DB_PASSWORD=your_database_password_here

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
   - Copy the **Password** (SUPABASE_DB_PASSWORD) - Used for direct PostgreSQL connections

### 🔄 Database Setup & Migrations

This project uses **Sqitch** for database schema management with automated GitHub Actions deployment.

#### Database Schema
The database includes tables for:
- **clips**: Link storage and metadata
- **user_clips**: User-owned clips with RLS
- **collections**: User clip collections
- **tags**: Tagging system
- **jobs**: Background job processing

#### Local Database Setup
```bash
# Navigate to database directory
cd db

# Deploy migrations locally (requires SUPABASE_URL and SUPABASE_DB_PASSWORD in environment)
./deploy.sh
```

#### CI/CD Setup
For automated database migrations via GitHub Actions:

1. **Configure GitHub Secrets**: 
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_DB_PASSWORD`: Your database password
2. **Auto-deploy**: Migrations run automatically on pushes to `main` branch
3. **Manual deploy**: Use "Run workflow" in GitHub Actions for manual deployment

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

#### Unit Tests
```bash
# Run all tests
poetry run pytest

# Run auth tests specifically
poetry run pytest tests/test_auth.py -v

# Run database tests
poetry run pytest tests/test_supabase.py -v

# Run with coverage
poetry run pytest --cov=api tests/
```

#### OAuth Integration Testing
For end-to-end OAuth testing with real Google authentication:

```bash
# 1. Start the API server
poetry run uvicorn api.main:app --reload

# 2. Open the interactive test page
open oauth_test.html

# 3. Configure your Supabase credentials in the HTML form
# 4. Test the complete OAuth flow: Supabase → Google → API

# Or test with curl (requires real OAuth code)
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "code": "your-real-oauth-code",
    "code_verifier": "your-pkce-verifier"
  }'
```

See `OAUTH_TESTING_GUIDE.md` for detailed OAuth testing instructions.

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/ping
```

#### Authentication
```bash
# OAuth token exchange (Google authorization code → JWT)
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "code": "your-oauth-authorization-code",
    "code_verifier": "your-pkce-code-verifier",
    "redirect_uri": "your-redirect-uri"
  }'

# Get current user profile (requires valid JWT token)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/auth/me

# Verify token validity
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

#### Option 1: OAuth Code Exchange (Production)
Use the `/auth/token` endpoint to exchange Google OAuth authorization codes for JWT tokens:

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "code": "4/0AanBODAyNGpYGJKqBFyI-your-auth-code",
    "code_verifier": "your-pkce-code-verifier",
    "redirect_uri": "http://localhost:3000/auth/callback"
  }'
```

#### Option 2: Supabase Direct (Recommended for Frontend)
Use Supabase client libraries directly in your frontend:

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Sign in with Google
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})

// Get the JWT from the session
const { data: { session } } = await supabase.auth.getSession()
const jwt = session?.access_token
```

#### Option 3: Interactive Testing
Use the included HTML test page for OAuth flow testing:

```bash
# Open the test page
open oauth_test.html

# Configure your Supabase credentials
# Test both Supabase OAuth and API endpoints
```

### Supported Endpoints

- `POST /auth/token` - OAuth code exchange (Google → JWT) ✅
- `GET /auth/me` - Get current user profile ✅  
- `GET /auth/verify` - Verify token validity ✅

## Project Structure

```
api/
├── main.py                 # FastAPI application with lifespan management
├── routes/
│   └── auth.py            # Authentication routes (/auth/token, /auth/me, /auth/verify)
├── services/
│   ├── auth.py            # Authentication service & JWT validation
│   ├── supabase.py        # Supabase PostgreSQL connection service
│   └── database.py        # Database dependencies for FastAPI
└── schemas/
    └── auth.py            # Pydantic models for auth requests/responses

db/                         # Database migrations (Sqitch)
├── sqitch.conf            # Sqitch configuration
├── sqitch.plan            # Migration plan
├── deploy/                # SQL migration files
├── revert/                # SQL rollback files
├── verify/                # SQL verification files
└── deploy.sh              # Local deployment script

tests/
├── test_auth.py           # Authentication tests
├── test_main.py           # Main application tests
└── test_supabase.py       # Database service tests

.github/workflows/
└── database.yml           # Automated database deployment

oauth_test.html             # Interactive OAuth testing page
OAUTH_TESTING_GUIDE.md     # OAuth testing documentation
```

## Task Status

### ✅ Completed Tasks

**API-AUTH-003**: Supabase Auth middleware - COMPLETED
- [x] JWKS fetching and caching  
- [x] JWT verification with python-jose
- [x] FastAPI dependency `get_current_user()`
- [x] 401/403 exception handlers
- [x] `/auth/me` endpoint with user profile
- [x] `/auth/verify` endpoint for token validation
- [x] Comprehensive test suite

**API-DB-004**: Supabase Postgres wrapper - COMPLETED
- [x] AsyncPG connection pooling
- [x] Row Level Security (RLS) support
- [x] Connection string configuration for Supabase pooler
- [x] Database health checks
- [x] FastAPI dependencies for database injection
- [x] Comprehensive test suite

**API-DB-005**: Database migrations - COMPLETED
- [x] Sqitch migration system setup
- [x] Database schema (clips, user_clips, collections, tags, jobs)
- [x] Database indices for performance
- [x] Row Level Security policies
- [x] GitHub Actions CI/CD for automated deployment
- [x] Local development scripts

**API-ROUTE-006**: OAuth token exchange - COMPLETED
- [x] `/auth/token` endpoint implementation
- [x] Google OAuth authorization code exchange
- [x] PKCE flow support
- [x] User profile extraction from Supabase response
- [x] Error handling for invalid codes/providers
- [x] Interactive HTML test page
- [x] Comprehensive test suite

### 🚧 Next Steps

- **API-ROUTE-008**: `/clips` POST endpoint for link ingestion
- **API-ROUTE-009**: `/clips` GET endpoint for clip retrieval  
- **API-ROUTE-010**: Collection management endpoints
- **API-ROUTE-011**: Search and filtering endpoints

## Docker Development

```bash
# Build and run with docker-compose
docker-compose up --build

# API will be available at http://localhost:8000
```

## Production Deployment

This API is designed for deployment on **Google Cloud Run**. See the `docker/` and infrastructure configuration for deployment details.

---

## 📚 Documentation

- **[LLD Public API](.context/LLD%20Public%20API.md)** - Low-level design document
- **[Task Breakdown](.context/Task%20Breakdown%20for%20Public%20API.md)** - Development task breakdown
- **[OAuth Testing Guide](OAUTH_TESTING_GUIDE.md)** - Complete OAuth testing instructions
- **Interactive Testing**: `oauth_test.html` - Browser-based OAuth testing tool

## 🎯 Current Status

**Production Ready Components:**
- ✅ Authentication system (Google OAuth + JWT)
- ✅ Database integration with RLS  
- ✅ Automated migrations and deployments
- ✅ Comprehensive testing framework

**Next Development Phase:**
- 🚧 Clip ingestion and retrieval endpoints
- 🚧 Collection management system
- 🚧 Search and filtering capabilities 