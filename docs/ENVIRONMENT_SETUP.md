# ClipVault API - Environment Configuration Guide

This document outlines all the environment variables required for the ClipVault Public API.

## **🔧 Required Environment Variables**

### **Application Configuration**
```bash
# Application environment (development, staging, production)
ENVIRONMENT=development

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

### **Supabase Configuration**
```bash
# Supabase project URL
SUPABASE_URL=https://your-project.supabase.co

# Supabase public anonymous key
SUPABASE_ANON_KEY=your-anon-key-here

# Supabase service role key (full access)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# JWT secret for token verification
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Database connection string
DATABASE_URL=postgresql://postgres:your-service-role-key@db.your-project-ref.supabase.co:5432/postgres
```

### **Google Cloud Pub/Sub Configuration**
```bash
# Google Cloud Project ID (required for Pub/Sub)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Pub/Sub topic names (as created in infrastructure setup)
PUBSUB_CLIP_EVENTS_TOPIC=clip-events
PUBSUB_CLIP_EVENTS_DLQ_TOPIC=clip-events-dlq
```

### **Security Configuration**
```bash
# CORS origins (comma-separated for multiple origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Allow credentials in CORS requests
CORS_ALLOW_CREDENTIALS=true

# Disable API documentation in production
DISABLE_DOCS=false
```

## **🌍 Environment-Specific Configurations**

### **Local Development**
```bash
# Copy this to your local .env file
ENVIRONMENT=development
LOG_LEVEL=DEBUG
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
PUBSUB_CLIP_EVENTS_TOPIC=clip-events
PUBSUB_CLIP_EVENTS_DLQ_TOPIC=clip-events-dlq
CORS_ORIGINS=http://localhost:3000
DISABLE_DOCS=false
```

### **Cloud Run Production**
```bash
# Set these as environment variables in Cloud Run
ENVIRONMENT=production
LOG_LEVEL=INFO
SUPABASE_URL=https://your-production-project.supabase.co
SUPABASE_ANON_KEY=your-production-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-production-service-role-key
SUPABASE_JWT_SECRET=your-production-jwt-secret
GOOGLE_CLOUD_PROJECT=your-production-gcp-project-id
PUBSUB_CLIP_EVENTS_TOPIC=clip-events
PUBSUB_CLIP_EVENTS_DLQ_TOPIC=clip-events-dlq
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
DISABLE_DOCS=true
```

## **🔒 Security Notes**

### **Credentials Management:**
- **Never commit `.env` files** to version control
- **Use Google Cloud Secret Manager** for production secrets
- **Use Application Default Credentials** for Google Cloud services
- **Rotate keys regularly** in production

### **Required Permissions:**
- **Supabase Service Role**: Full access to your Supabase project
- **Google Cloud Service Account**: `roles/pubsub.publisher` permission
- **Database**: Connection access to Supabase Postgres

## **🧪 Testing Configuration**

For running tests, you may need additional variables:
```bash
# Test database (optional - uses in-memory if not provided)
TEST_DATABASE_URL=postgresql://postgres:test-password@localhost:5432/clipvault_test

# Disable external services in tests
GOOGLE_CLOUD_PROJECT=test-project
```

## **📋 Environment Setup Checklist**

### Local Development:
- [ ] Create `.env` file in project root
- [ ] Set all required variables from the local development section
- [ ] Run `gcloud auth application-default login`
- [ ] Verify with `uvicorn api.main:app --reload`

### Cloud Run Deployment:
- [ ] Set environment variables in Cloud Run service configuration
- [ ] Attach service account with Pub/Sub permissions
- [ ] Verify deployment with health check endpoint

## **🔍 Environment Validation**

The API includes environment validation on startup. If required variables are missing, you'll see clear error messages in the logs.

**Startup validation checks:**
- ✅ Supabase configuration completeness
- ✅ Google Cloud project accessibility  
- ✅ Pub/Sub topic permissions
- ✅ Database connectivity

---

**Next Steps:**
1. Configure your environment using this guide
2. Start the development server
3. Verify all services are working via `/health` endpoint 