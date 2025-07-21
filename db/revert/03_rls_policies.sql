-- Revert clipvault-schema:03_rls_policies from pg

BEGIN;

-- Drop security definer function
DROP FUNCTION IF EXISTS bypass_rls_for_api();

-- Drop all RLS policies
DROP POLICY IF EXISTS user_clips_owner_policy ON user_clips;
DROP POLICY IF EXISTS collections_owner_policy ON collections;
DROP POLICY IF EXISTS collections_public_read_policy ON collections;
DROP POLICY IF EXISTS collections_clips_owner_policy ON collections_clips;
DROP POLICY IF EXISTS collections_clips_public_read_policy ON collections_clips;
DROP POLICY IF EXISTS clips_read_policy ON clips;
DROP POLICY IF EXISTS clips_system_write_policy ON clips;
DROP POLICY IF EXISTS clips_system_update_policy ON clips;
DROP POLICY IF EXISTS tags_read_policy ON tags;
DROP POLICY IF EXISTS tags_system_write_policy ON tags;
DROP POLICY IF EXISTS tags_system_update_policy ON tags;
DROP POLICY IF EXISTS clip_tags_read_policy ON clip_tags;
DROP POLICY IF EXISTS clip_tags_system_write_policy ON clip_tags;
DROP POLICY IF EXISTS clip_tags_system_update_policy ON clip_tags;
DROP POLICY IF EXISTS clip_tags_system_delete_policy ON clip_tags;
DROP POLICY IF EXISTS jobs_system_policy ON jobs;

-- Disable Row Level Security on all tables
ALTER TABLE user_clips DISABLE ROW LEVEL SECURITY;
ALTER TABLE collections DISABLE ROW LEVEL SECURITY;
ALTER TABLE collections_clips DISABLE ROW LEVEL SECURITY;
ALTER TABLE clips DISABLE ROW LEVEL SECURITY;
ALTER TABLE tags DISABLE ROW LEVEL SECURITY;
ALTER TABLE clip_tags DISABLE ROW LEVEL SECURITY;
ALTER TABLE jobs DISABLE ROW LEVEL SECURITY;

COMMIT; 