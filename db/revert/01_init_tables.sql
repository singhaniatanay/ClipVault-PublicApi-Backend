-- Revert clipvault-schema:01_init_tables from pg

BEGIN;

-- Drop triggers first
DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
DROP TRIGGER IF EXISTS update_collections_updated_at ON collections;
DROP TRIGGER IF EXISTS update_tags_updated_at ON tags;
DROP TRIGGER IF EXISTS update_clips_updated_at ON clips;

-- Drop trigger function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS collections_clips;
DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS clip_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS user_clips;
DROP TABLE IF EXISTS clips;

-- Note: We don't drop extensions as they might be used by other schemas

COMMIT; 