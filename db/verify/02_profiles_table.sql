-- Verify clipvault-schema:02_profiles_table on pg

BEGIN;

-- Verify table exists
SELECT 1/COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'profiles';

-- Verify primary key exists
SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'profiles' AND constraint_type = 'PRIMARY KEY';

-- Verify foreign key exists
SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'profiles' AND constraint_type = 'FOREIGN KEY';

-- Verify check constraints exist
SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'profiles' AND constraint_type = 'CHECK';

-- Verify RLS is enabled
SELECT 1/COUNT(*) FROM pg_tables 
WHERE tablename = 'profiles' AND rowsecurity = true;

-- Verify policies exist
SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'profiles' AND policyname = 'Users can view own profile';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'profiles' AND policyname = 'Users can update own profile';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'profiles' AND policyname = 'Users can insert own profile';

-- Verify indexes exist
SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'profiles' AND indexname = 'idx_profiles_user_id';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'profiles' AND indexname = 'idx_profiles_digest_enabled';

-- Verify trigger exists
SELECT 1/COUNT(*) FROM pg_trigger 
WHERE tgname = 'update_profiles_updated_at';

COMMIT; 