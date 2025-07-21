#!/bin/bash

# Test Database Connection Script
# This script helps verify your environment is set up correctly for database migrations

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo_info "🧪 ClipVault Database Connection Test"
echo_info "======================================"

# Load environment variables from .env if it exists
if [[ -f ".env" ]]; then
    echo_info "Loading environment variables from .env file"
    set -a
    source .env
    set +a
else
    echo_warning "No .env file found. Using system environment variables."
fi

# Check required environment variables
echo_info "Checking environment variables..."

if [[ -z "${SUPABASE_URL:-}" ]]; then
    echo_error "SUPABASE_URL is not set"
    echo_info "Set it to your Supabase project URL (e.g., https://your-project.supabase.co)"
    exit 1
else
    echo_success "SUPABASE_URL is set: $SUPABASE_URL"
fi

if [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
    echo_error "SUPABASE_DB_PASSWORD is not set"
    echo_info "Set it to your Supabase database password"
    exit 1
else
    echo_success "SUPABASE_DB_PASSWORD is set (length: ${#SUPABASE_DB_PASSWORD} characters)"
fi

# Extract project reference
echo_info "Extracting project reference from URL..."
PROJECT_REF=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co||')

if [[ -z "$PROJECT_REF" ]]; then
    echo_error "Failed to extract project reference from URL: $SUPABASE_URL"
    echo_info "Expected format: https://your-project-id.supabase.co"
    exit 1
else
    echo_success "Project reference: $PROJECT_REF"
fi

# Build connection string
DATABASE_URL="postgresql://postgres.$PROJECT_REF:$SUPABASE_DB_PASSWORD@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
echo_success "Connection string built successfully"
echo_info "Connection details: postgres.$PROJECT_REF@aws-0-us-east-2.pooler.supabase.com:6543"

# Check if psql is available for testing
if command -v psql >/dev/null 2>&1; then
    echo_info "Testing database connection with psql..."
    
    if psql "$DATABASE_URL" -c "SELECT 1 as test;" >/dev/null 2>&1; then
        echo_success "Database connection successful!"
        
        # Get some basic info
        echo_info "Database information:"
        psql "$DATABASE_URL" -c "SELECT version();" 2>/dev/null | head -3 || echo_warning "Could not get version info"
        
    else
        echo_error "Database connection failed"
        echo_info "Check your SUPABASE_DB_PASSWORD and ensure your IP is allowlisted"
        exit 1
    fi
else
    echo_warning "psql not available for connection testing"
    echo_info "Install PostgreSQL client to test connections"
fi

# Check if Sqitch is available
if command -v sqitch >/dev/null 2>&1; then
    echo_success "Sqitch is available"
    
    # Test sqitch configuration
    if [[ -f "db/sqitch.plan" ]]; then
        echo_info "Testing Sqitch configuration..."
        cd db/
        
        echo_info "Planned migrations:"
        cat sqitch.plan | grep -v '^%\|^$\|^#'
        
        echo_info "Checking migration status..."
        if sqitch status "$DATABASE_URL" 2>/dev/null; then
            echo_success "Sqitch can connect to database"
        else
            echo_warning "Sqitch status check failed (this is normal if no migrations are deployed yet)"
        fi
        
        cd ..
    else
        echo_warning "No sqitch.plan found in db/ directory"
    fi
else
    echo_warning "Sqitch not available"
    echo_info "Install with: brew install sqitch --with-postgres-support"
    echo_info "Or on Ubuntu: sudo apt-get install sqitch libdbd-pg-perl"
fi

echo_info "======================================"
echo_success "🎉 Environment test completed!"
echo_info "If all checks passed, you're ready to run database migrations."
echo_info ""
echo_info "Next steps:"
echo_info "1. Deploy migrations locally: cd db && ./deploy.sh"
echo_info "2. Configure GitHub secrets for CI/CD (see docs/GITHUB_SETUP.md)"
echo_info "3. Push to trigger automated deployments" 