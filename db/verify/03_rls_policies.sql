-- Verify clipvault-schema:03_rls_policies on pg

BEGIN;

-- Verify RLS is enabled on the correct tables
SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'user_clips' AND relrowsecurity = true;

SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'collections' AND relrowsecurity = true;

SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'collections_clips' AND relrowsecurity = true;

SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'clips' AND relrowsecurity = true;

SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'tags' AND relrowsecurity = true;

SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'clip_tags' AND relrowsecurity = true;

SELECT 1/COUNT(*) FROM pg_class 
WHERE relname = 'jobs' AND relrowsecurity = true;

-- Verify key policies exist
SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'user_clips' AND policyname = 'user_clips_owner_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'collections' AND policyname = 'collections_owner_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'collections' AND policyname = 'collections_public_read_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'collections_clips' AND policyname = 'collections_clips_owner_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'collections_clips' AND policyname = 'collections_clips_public_read_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clips' AND policyname = 'clips_read_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clips' AND policyname = 'clips_system_write_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clips' AND policyname = 'clips_system_update_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'tags' AND policyname = 'tags_read_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'tags' AND policyname = 'tags_system_write_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'tags' AND policyname = 'tags_system_update_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clip_tags' AND policyname = 'clip_tags_read_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clip_tags' AND policyname = 'clip_tags_system_write_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clip_tags' AND policyname = 'clip_tags_system_update_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'clip_tags' AND policyname = 'clip_tags_system_delete_policy';

SELECT 1/COUNT(*) FROM pg_policies 
WHERE tablename = 'jobs' AND policyname = 'jobs_system_policy';

-- Verify security definer function exists
SELECT 1/COUNT(*) FROM information_schema.routines 
WHERE routine_name = 'bypass_rls_for_api' 
  AND security_type = 'DEFINER';

ROLLBACK; 