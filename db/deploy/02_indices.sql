-- Deploy clipvault-schema:02_indices to pg
-- requires: 01_init_tables

BEGIN;

-- Full-text search index on clips (as specified in LLD)
-- This enables fast keyword search across transcript and summary
CREATE INDEX clips_fts_idx ON clips USING gin (
    to_tsvector('english', coalesce(transcript, '') || ' ' || coalesce(summary, ''))
);

-- Performance index for user clips (as specified in LLD)
-- Optimizes queries for user's saved clips ordered by save time
CREATE INDEX user_clips_uid_saved_idx ON user_clips (owner_uid, saved_at DESC);

-- Additional performance indices for common query patterns

-- Index for clips by status and creation time (for admin/processing views)
CREATE INDEX clips_status_created_idx ON clips (status, created_at DESC);

-- Index for clips by source URL for deduplication lookups
CREATE INDEX clips_source_url_idx ON clips (source_url);

-- Index for tags by usage count (for popular tags queries)
CREATE INDEX tags_usage_count_idx ON tags (usage_count DESC, name);

-- Index for tags by name (for tag search/autocomplete)
CREATE INDEX tags_name_trgm_idx ON tags USING gin (name gin_trgm_ops);

-- Index for collections by owner (for user's collections)
CREATE INDEX collections_owner_idx ON collections (owner_uid, created_at DESC);

-- Index for collection clips by collection (for collection content)
CREATE INDEX collections_clips_coll_idx ON collections_clips (coll_id, added_at DESC);

-- Index for clip tags by clip (for getting clip's tags)
CREATE INDEX clip_tags_clip_idx ON clip_tags (clip_id, confidence_score DESC);

-- Index for clip tags by tag (for finding clips with specific tag)
CREATE INDEX clip_tags_tag_idx ON clip_tags (tag_id, confidence_score DESC);

-- Index for jobs by status and priority (for job queue processing)
CREATE INDEX jobs_status_priority_idx ON jobs (status, priority DESC, created_at ASC);

-- Index for jobs by clip (for checking clip processing status)
CREATE INDEX jobs_clip_idx ON jobs (clip_id, job_type, status);

-- Partial index for active jobs only (excludes completed/failed jobs for faster queue queries)
CREATE INDEX jobs_active_idx ON jobs (priority DESC, created_at ASC) 
WHERE status IN ('pending', 'running');

COMMIT; 