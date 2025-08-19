-- Revert clipvault-schema:02_profiles_table from pg

BEGIN;

-- Drop trigger first
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;

-- Drop trigger function
DROP FUNCTION IF EXISTS update_profiles_updated_at();

-- Drop policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;

-- Drop indexes
DROP INDEX IF EXISTS idx_profiles_digest_enabled;
DROP INDEX IF EXISTS idx_profiles_user_id;

-- Drop table
DROP TABLE IF EXISTS public.profiles;

COMMIT; 