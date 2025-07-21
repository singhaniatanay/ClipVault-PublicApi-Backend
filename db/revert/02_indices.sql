-- Revert clipvault-schema:02_indices from pg

BEGIN;

-- Drop all indices created in 02_indices migration
DROP INDEX IF EXISTS clips_fts_idx;
DROP INDEX IF EXISTS user_clips_uid_saved_idx;
DROP INDEX IF EXISTS clips_status_created_idx;
DROP INDEX IF EXISTS clips_source_url_idx;
DROP INDEX IF EXISTS tags_usage_count_idx;
DROP INDEX IF EXISTS tags_name_trgm_idx;
DROP INDEX IF EXISTS collections_owner_idx;
DROP INDEX IF EXISTS collections_clips_coll_idx;
DROP INDEX IF EXISTS clip_tags_clip_idx;
DROP INDEX IF EXISTS clip_tags_tag_idx;
DROP INDEX IF EXISTS jobs_status_priority_idx;
DROP INDEX IF EXISTS jobs_clip_idx;
DROP INDEX IF EXISTS jobs_active_idx;

COMMIT; 