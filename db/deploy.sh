#!/bin/bash

# ClipVault Database Migration Deployment Script
# Usage: ./deploy.sh [environment]
# Environment: local, staging, production (default: local)

set -euo pipefail

ENVIRONMENT=${1:-local}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Check if we're in the db directory
if [[ ! -f "sqitch.plan" ]]; then
    echo_error "Please run this script from the db/ directory"
    echo_info "Current directory: $(pwd)"
    exit 1
fi

# Check if Sqitch is installed
if ! command -v sqitch &> /dev/null; then
    echo_error "Sqitch is not installed"
    echo_info "Install with: brew install sqitch --with-postgres-support"
    echo_info "Or on Ubuntu: sudo apt-get install sqitch libdbd-pg-perl"
    exit 1
fi

# Load environment variables
if [[ -f "../.env" ]]; then
    echo_info "Loading environment variables from .env file"
    set -a
    source ../.env
    set +a
fi

# Validate required environment variables
case $ENVIRONMENT in
    local|staging)
        if [[ -z "${SUPABASE_URL:-}" ]] || [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
            echo_error "Missing required environment variables:"
            echo_info "SUPABASE_URL and SUPABASE_DB_PASSWORD must be set"
            exit 1
        fi
        PROJECT_REF=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co||')
        DATABASE_URL="postgresql://postgres.${PROJECT_REF}:${SUPABASE_DB_PASSWORD}@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
        ;;
    production)
        if [[ -z "${SUPABASE_URL:-}" ]] || [[ -z "${SUPABASE_DB_PASSWORD:-}" ]]; then
            echo_error "Missing required environment variables:"
            echo_info "SUPABASE_URL and SUPABASE_DB_PASSWORD must be set"
            exit 1
        fi
        PROJECT_REF=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co||')
        DATABASE_URL="postgresql://postgres.${PROJECT_REF}:${SUPABASE_DB_PASSWORD}@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
        ;;
    *)
        echo_error "Invalid environment: $ENVIRONMENT"
        echo_info "Valid environments: local, staging, production"
        exit 1
        ;;
esac

echo_info "Deploying migrations to $ENVIRONMENT environment"
echo_info "Project reference: $PROJECT_REF"
echo_info "Database host: aws-0-us-east-2.pooler.supabase.com:6543"

# Check current migration status
echo_info "Checking current migration status..."
if sqitch status "$DATABASE_URL" 2>/dev/null; then
    echo_success "Connected to database successfully"
else
    echo_warning "Could not connect to database or no migrations deployed yet"
fi

# Confirm deployment for production
if [[ $ENVIRONMENT == "production" ]]; then
    echo_warning "⚠️  You are about to deploy to PRODUCTION!"
    echo_info "This will apply migrations to the production database."
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo_info "Deployment cancelled"
        exit 0
    fi
fi

# Pre-deployment checks
echo_info "Running pre-deployment checks..."
echo_info "Planned migrations:"
cat sqitch.plan | grep -v '^%\|^$\|^#'

echo_info "Checking migration file completeness..."
while IFS= read -r line; do
    if [[ $line =~ ^([a-zA-Z0-9_]+) ]]; then
        migration="${BASH_REMATCH[1]}"
        if [[ ! -f "deploy/$migration.sql" ]] || [[ ! -f "revert/$migration.sql" ]] || [[ ! -f "verify/$migration.sql" ]]; then
            echo_error "Missing migration files for: $migration"
            exit 1
        fi
    fi
done < <(grep -v '^%\|^$\|^#' sqitch.plan)

echo_success "Pre-deployment checks passed"

# Deploy migrations
echo_info "Deploying migrations to $ENVIRONMENT..."
if sqitch deploy "$DATABASE_URL"; then
    echo_success "Migrations deployed successfully!"
else
    echo_error "Migration deployment failed"
    
    # Attempt rollback for production
    if [[ $ENVIRONMENT == "production" ]]; then
        echo_warning "Attempting automatic rollback..."
        if sqitch revert --to @HEAD~1 "$DATABASE_URL"; then
            echo_success "Rollback successful"
        else
            echo_error "Rollback failed - manual intervention required!"
        fi
    fi
    exit 1
fi

# Verify deployment
echo_info "Verifying deployed migrations..."
if sqitch verify "$DATABASE_URL"; then
    echo_success "Migration verification passed"
else
    echo_error "Migration verification failed after deployment"
    exit 1
fi

# Show final status
echo_info "Final migration status:"
sqitch status "$DATABASE_URL"

echo_success "🎉 Database deployment to $ENVIRONMENT completed successfully!"

# Show next steps
case $ENVIRONMENT in
    local|staging)
        echo_info "🔗 Check your database in Supabase Studio: $SUPABASE_URL"
        ;;
    production)
        echo_info "🔗 Check your database in Supabase Studio: $PRODUCTION_SUPABASE_URL"
        ;;
esac

echo_info "📊 You can now test the API with the updated schema" 