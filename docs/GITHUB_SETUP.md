# GitHub Actions Setup for Database Migrations

## Required GitHub Secrets

To enable automatic database migrations via GitHub Actions, you need to configure the following secrets in your repository:

### 🔧 How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

### 📋 Required Secrets

#### For Staging Environment

| Secret Name | Description | Where to Find |
|-------------|-------------|---------------|
| `SUPABASE_URL` | Your Supabase project URL | Supabase Dashboard → Settings → API |
| `SUPABASE_DB_PASSWORD` | Database password | Supabase Dashboard → Settings → Database |

#### For Production Environment (if different from staging)

| Secret Name | Description | Where to Find |
|-------------|-------------|---------------|
| `PRODUCTION_SUPABASE_URL` | Production Supabase project URL | Production Supabase Dashboard → Settings → API |
| `PRODUCTION_SUPABASE_DB_PASSWORD` | Production database password | Production Supabase Dashboard → Settings → Database |

### 🔍 Finding Your Supabase Credentials

#### 1. Supabase URL
- Go to [Supabase Dashboard](https://supabase.com/dashboard)
- Select your project
- Go to **Settings** → **API**
- Copy the **URL** (format: `https://your-project-id.supabase.co`)

#### 2. Database Password
- In Supabase Dashboard, go to **Settings** → **Database**
- Look for **Connection pooling** section
- The password is the same as your project's database password
- If you don't have it, you can reset it in the **Database** settings

### ✅ Verification

After adding the secrets, you can verify they work by:

1. **Manual Testing** (locally):
   ```bash
   # Set your environment variables
   export SUPABASE_URL="https://your-project-id.supabase.co"
   export SUPABASE_DB_PASSWORD="your-password"
   
   # Test the connection
   cd db/
   ./deploy.sh
   ```

2. **GitHub Actions Testing**:
   - Push changes to a feature branch
   - Create a pull request
   - The "verify-migrations" job should run successfully
   - Check the workflow logs for any secret-related errors

### 🚨 Troubleshooting

#### Error: "SUPABASE_URL secret is not set!"
- Verify the secret name matches exactly: `SUPABASE_URL` (case-sensitive)
- Check that you're in the correct repository
- Ensure the secret has a value and isn't empty

#### Error: "Failed to extract project reference from URL"
- Verify your URL format: `https://your-project-id.supabase.co`
- No trailing slashes or additional paths
- Must include `https://` prefix

#### Error: "Unknown argument" with connection string
- Usually means the `PROJECT_REF` extraction failed
- Check your `SUPABASE_URL` format
- Verify the URL extraction logic works with your specific URL

#### Connection timeout or authentication errors
- Verify your `SUPABASE_DB_PASSWORD` is correct
- Check if your IP is allowlisted in Supabase (Settings → Authentication → URL Configuration)
- Ensure you're using the database password, not the service role key

### 🔄 Workflow Triggers

The database migration workflow runs automatically:

- **Pull Requests**: File verification only (no deployment)
- **Push to `develop` branch**: Deploy to staging
- **Push to `main` branch**: Deploy to production
- **Manual trigger**: Deploy to chosen environment

### 📚 Related Documentation

- [Supabase Database Guide](https://supabase.com/docs/guides/database)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Sqitch Documentation](https://sqitch.org/docs/)
- [ClipVault Database Migrations](../db/README.md) 