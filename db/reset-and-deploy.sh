#!/bin/bash

# Script to reset sqitch state and redeploy migrations
# This resolves the hash mismatch issue between database state and sqitch.plan

set -e

echo "🔄 Starting database reset and redeployment..."

# Check if DATABASE_URL is set
if [[ -z "$DATABASE_URL" ]]; then
    echo "❌ DATABASE_URL environment variable is required"
    echo "   Format: db:pg://postgres.PROJECT_REF:PASSWORD@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
    exit 1
fi

echo "🔗 Database URL: ${DATABASE_URL//:*@/:***@}"

# Function to run sqitch commands with error handling
run_sqitch() {
    local cmd="$1"
    local description="$2"
    
    echo "📋 $description..."
    if sqitch "$cmd" "$DATABASE_URL"; then
        echo "✅ $description completed successfully"
    else
        echo "❌ $description failed"
        return 1
    fi
}

# Check current status
echo "📊 Current migration status:"
sqitch status "$DATABASE_URL" || echo "No previous migrations or connection issues"

# Option 1: Try to revert all migrations to clean state
echo ""
echo "🔄 Attempting to revert all migrations..."
if sqitch revert --to @ROOT "$DATABASE_URL" 2>/dev/null; then
    echo "✅ Successfully reverted all migrations"
else
    echo "⚠️  Revert failed or no migrations to revert"
    echo "🔄 Attempting manual cleanup of sqitch registry..."
    
    # Option 2: Manually clean sqitch registry
    psql "$DATABASE_URL" -c "
        DO \$\$
        BEGIN
            -- Drop sqitch schema if it exists
            IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'sqitch') THEN
                DROP SCHEMA sqitch CASCADE;
                RAISE NOTICE 'Dropped sqitch schema and all related objects';
            ELSE
                RAISE NOTICE 'No sqitch schema found to clean';
            END IF;
        END
        \$\$;
    " || echo "⚠️  Manual cleanup failed - this may be expected if schema doesn't exist"
fi

# Deploy fresh migrations
echo ""
echo "🚀 Deploying migrations with corrected plan..."
run_sqitch "deploy" "Migration deployment"

# Verify deployment
echo ""
echo "🔍 Verifying deployment..."
run_sqitch "verify" "Migration verification"

# Show final status
echo ""
echo "📊 Final migration status:"
sqitch status "$DATABASE_URL"

echo ""
echo "✅ Database reset and redeployment completed successfully!"
echo "🎉 All migrations are now in sync with the current sqitch.plan"
