# Sqitch Hash Mismatch Resolution

## Problem
The deployment was failing with this error:
```
Cannot find change 1151f1bf400653ca18594f816e66b0e09437473d (03_rls_policies) in sqitch.plan
```

## Root Cause
The sqitch plan was restructured:
- `03_rls_policies` was renamed to `04_rls_policies`
- A new `03_indices` migration was inserted
- This created a hash mismatch between the database state and current plan

## Solution

### Option 1: GitHub Actions Reset (Recommended)
1. Go to the GitHub repository
2. Navigate to **Actions** tab
3. Select **Database Migrations** workflow
4. Click **Run workflow**
5. Set **Reset database state** to `true`
6. Click **Run workflow**

This will:
- Reset the database to a clean state
- Redeploy all migrations with the corrected plan
- Verify the deployment

### Option 2: Manual Script Execution
If you have direct database access:
```bash
cd db/
export DATABASE_URL="db:pg://postgres.PROJECT_REF:PASSWORD@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
./reset-and-deploy.sh
```

## Prevention
To avoid this issue in the future:
- **Never rename or reorder existing migrations** after they've been deployed
- **Always append new migrations** to the end of sqitch.plan
- Use **dependency declarations** if migration order is important

## Files Modified
- `db/reset-and-deploy.sh` - Reset script
- `.github/workflows/database.yml` - Added reset option
- `db/SQITCH_RESET_INSTRUCTIONS.md` - This documentation

## Current Plan Structure
```
01_init_tables
02_profiles_table  
03_indices         ← New migration inserted here
04_rls_policies    ← Previously was 03_rls_policies
04_ai_processing_fields
```

