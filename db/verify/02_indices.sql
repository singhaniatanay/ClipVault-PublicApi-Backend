-- Verify clipvault-schema:02_indices on pg

BEGIN;

-- Verify primary FTS index exists (required by LLD)
SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'clips' AND indexname = 'clips_fts_idx';

-- Verify user clips performance index exists (required by LLD)
SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'user_clips' AND indexname = 'user_clips_uid_saved_idx';

-- Verify additional performance indices exist
SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'clips' AND indexname = 'clips_status_created_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'clips' AND indexname = 'clips_source_url_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'tags' AND indexname = 'tags_usage_count_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'tags' AND indexname = 'tags_name_trgm_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'collections' AND indexname = 'collections_owner_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'collections_clips' AND indexname = 'collections_clips_coll_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'clip_tags' AND indexname = 'clip_tags_clip_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'clip_tags' AND indexname = 'clip_tags_tag_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'jobs' AND indexname = 'jobs_status_priority_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'jobs' AND indexname = 'jobs_clip_idx';

SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'jobs' AND indexname = 'jobs_active_idx';

-- Verify FTS index is using GIN method
SELECT 1/COUNT(*) FROM pg_indexes 
WHERE tablename = 'clips' 
  AND indexname = 'clips_fts_idx' 
  AND indexdef LIKE '%gin%';

ROLLBACK; 