# ClipVault Database Migrations

This directory contains database schema migrations for ClipVault using [Sqitch](https://sqitch.org/).

## 📋 Overview

The ClipVault database schema includes:
- **7 core tables**: clips, user_clips, tags, clip_tags, collections, collections_clips, jobs
- **Full-text search indices** for efficient keyword search
- **Row Level Security (RLS)** policies for data isolation
- **Performance indices** optimized for common query patterns

## 🗄️ Schema Structure

### Core Tables

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `clips` | Canonical record per link | UNIQUE(source_url), FTS support |
| `user_clips` | User save history | PK(owner_uid, clip_id), RLS enabled |
| `tags` | Global tag catalog | UNIQUE(name), usage tracking |
| `clip_tags` | Clip tagging | Many-to-many with confidence scores |
| `collections` | User folders/smart rules | RLS enabled, public/private support |
| `collections_clips` | Collection membership | Many-to-many with sort order |
| `jobs` | AI processing status | System-managed, priority queue |

### Security Model

- **Row Level Security (RLS)** enforces data isolation
- Users can only access their own `user_clips` and `collections`
- Global read access to `clips`, `tags`, and `clip_tags`
- System-only write access to AI-managed tables

## 🚀 Quick Start

### Prerequisites

1. **Install Sqitch** (for local development):
   ```bash
   # macOS
   brew install sqitch --with-postgres-support
   
   # Ubuntu/Debian
   sudo apt-get install sqitch libdbd-pg-perl
   ```

2. **Environment Variables**:
   ```bash
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_DB_PASSWORD="your-database-password"
   ```

### Local Development

1. **Deploy migrations**:
   ```bash
   cd db/
   
   # Extract project reference
   PROJECT_REF=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co||')
   
   # Build connection string
   export DATABASE_URL="postgresql://postgres.${PROJECT_REF}:${SUPABASE_DB_PASSWORD}@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
   
   # Deploy all migrations
   sqitch deploy $DATABASE_URL
   ```

2. **Verify migrations**:
   ```bash
   sqitch verify $DATABASE_URL
   ```

3. **Check migration status**:
   ```bash
   sqitch status $DATABASE_URL
   ```

### Rollback (if needed)

```bash
# Rollback to previous migration
sqitch revert --to @HEAD~1 $DATABASE_URL

# Rollback specific migration
sqitch revert --to 02_indices $DATABASE_URL
```

## 📁 Migration Files

```
db/
├── sqitch.conf          # Sqitch configuration
├── sqitch.plan          # Migration plan/timeline
├── deploy/              # Forward migrations
│   ├── 01_init_tables.sql
│   ├── 02_indices.sql
│   └── 03_rls_policies.sql
├── revert/              # Rollback scripts
│   ├── 01_init_tables.sql
│   ├── 02_indices.sql
│   └── 03_rls_policies.sql
├── verify/              # Verification tests
│   ├── 01_init_tables.sql
│   ├── 02_indices.sql
│   └── 03_rls_policies.sql
└── README.md            # This file
```

## 🔄 CI/CD Integration

Migrations are automatically deployed via GitHub Actions:

- **Pull Requests**: Syntax verification and dry-run testing
- **`develop` branch**: Auto-deploy to staging database
- **`main` branch**: Auto-deploy to production database
- **Manual trigger**: Deploy to specific environment via workflow dispatch

### GitHub Secrets Required

| Secret | Description | Example |
|--------|-------------|---------|
| `SUPABASE_URL` | Staging Supabase project URL | `https://abc123.supabase.co` |
| `SUPABASE_DB_PASSWORD` | Staging database password | `your-staging-password` |
| `PRODUCTION_SUPABASE_URL` | Production Supabase project URL | `https://xyz789.supabase.co` |
| `PRODUCTION_SUPABASE_DB_PASSWORD` | Production database password | `your-production-password` |

## 🔍 Testing Migrations

### Local Testing

1. **Create test data**:
   ```sql
   -- Test user clips access (should work)
   SET request.jwt.claims.sub = 'user-123';
   INSERT INTO user_clips (owner_uid, clip_id) VALUES ('user-123', 'clip-uuid');
   SELECT * FROM user_clips; -- Should see your data
   
   -- Test RLS isolation (should be empty)
   SET request.jwt.claims.sub = 'user-456';
   SELECT * FROM user_clips; -- Should be empty
   ```

2. **Test FTS search**:
   ```sql
   INSERT INTO clips (source_url, transcript, summary) 
   VALUES ('https://example.com', 'Hello world', 'A greeting');
   
   -- Test full-text search
   SELECT * FROM clips 
   WHERE to_tsvector('english', coalesce(transcript, '') || ' ' || coalesce(summary, '')) 
         @@ plainto_tsquery('hello');
   ```

### Integration with API

The API uses these tables through the `SupabaseDB` service:

```python
# API automatically sets RLS context
await db.execute(
    "INSERT INTO user_clips (owner_uid, clip_id) VALUES ($1, $2)",
    user_id, clip_id,
    user_id=user_id  # Sets request.jwt.claims.sub
)
```

## 🛠️ Common Operations

### Adding New Migrations

1. **Create new migration**:
   ```bash
   sqitch add new_feature --note "Add new feature to database"
   ```

2. **Edit migration files**:
   - `deploy/new_feature.sql` - Forward migration
   - `revert/new_feature.sql` - Rollback script
   - `verify/new_feature.sql` - Verification test

3. **Test locally**:
   ```bash
   sqitch deploy
   sqitch verify
   sqitch revert --to @HEAD~1  # Test rollback
   sqitch deploy               # Re-deploy
   ```

### Checking Migration History

```bash
# Show deployed migrations
sqitch log

# Show migration status
sqitch status

# Show planned migrations
cat sqitch.plan
```

## 🚨 Troubleshooting

### Common Issues

1. **"No such file or directory" error**:
   - Ensure you're in the `db/` directory
   - Check that migration files exist in `deploy/`, `revert/`, `verify/`

2. **Connection timeout**:
   - Verify `SUPABASE_URL` and `SUPABASE_DB_PASSWORD`
   - Check if your IP is allowed in Supabase settings
   - Ensure connection string format is correct

3. **RLS policy errors**:
   - Verify `request.jwt.claims.sub` is set correctly
   - Check that user ID matches UUID format
   - Ensure service role has proper permissions

4. **Migration conflicts**:
   - Check `sqitch status` for current state
   - Use `sqitch revert` to rollback problematic migrations
   - Resolve conflicts in migration files

### Manual Recovery

If migrations fail in production:

1. **Check current state**:
   ```bash
   sqitch status $PRODUCTION_DATABASE_URL
   ```

2. **Rollback if needed**:
   ```bash
   sqitch revert --to last_known_good $PRODUCTION_DATABASE_URL
   ```

3. **Re-deploy after fixes**:
   ```bash
   sqitch deploy $PRODUCTION_DATABASE_URL
   ```

## 📚 Resources

- [Sqitch Documentation](https://sqitch.org/docs/)
- [Supabase Database Guide](https://supabase.com/docs/guides/database)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [ClipVault LLD](../.context/LLD%20Public%20API.md) 