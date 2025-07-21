-- Deploy clipvault-schema:03_rls_policies to pg
-- requires: 02_indices

BEGIN;

-- Enable Row Level Security on all user-owned tables
ALTER TABLE user_clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections_clips ENABLE ROW LEVEL SECURITY;

-- Note: clips, tags, clip_tags, and jobs tables are not user-specific
-- clips table is globally readable but write-protected
-- tags table is globally readable
-- clip_tags table inherits access from clips
-- jobs table is system-managed

-- User clips policies: Users can only access their own saved clips
CREATE POLICY user_clips_owner_policy ON user_clips
    FOR ALL
    USING (owner_uid = current_setting('request.jwt.claims.sub')::uuid)
    WITH CHECK (owner_uid = current_setting('request.jwt.claims.sub')::uuid);

-- Collections policies: Users can only access their own collections
CREATE POLICY collections_owner_policy ON collections
    FOR ALL
    USING (owner_uid = current_setting('request.jwt.claims.sub')::uuid)
    WITH CHECK (owner_uid = current_setting('request.jwt.claims.sub')::uuid);

-- Public collections policy: Allow read access to public collections
CREATE POLICY collections_public_read_policy ON collections
    FOR SELECT
    USING (is_public = true);

-- Collections clips policies: Users can only manage clips in their own collections
-- This policy checks if the collection belongs to the current user
CREATE POLICY collections_clips_owner_policy ON collections_clips
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM collections c 
            WHERE c.coll_id = collections_clips.coll_id 
            AND c.owner_uid = current_setting('request.jwt.claims.sub')::uuid
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM collections c 
            WHERE c.coll_id = collections_clips.coll_id 
            AND c.owner_uid = current_setting('request.jwt.claims.sub')::uuid
        )
    );

-- Public collections clips read policy: Allow reading clips from public collections
CREATE POLICY collections_clips_public_read_policy ON collections_clips
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM collections c 
            WHERE c.coll_id = collections_clips.coll_id 
            AND c.is_public = true
        )
    );

-- Clips table policies: Global read access, but only allow updates by system
-- Users can read all clips, but cannot modify them directly
-- All clip modifications go through the API layer
ALTER TABLE clips ENABLE ROW LEVEL SECURITY;

CREATE POLICY clips_read_policy ON clips
    FOR SELECT
    USING (true); -- Anyone can read clips

-- Only allow inserts/updates through API (no direct user access)
CREATE POLICY clips_system_write_policy ON clips
    FOR INSERT
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

CREATE POLICY clips_system_update_policy ON clips
    FOR UPDATE
    USING (current_setting('role') = 'service_role' OR current_user = 'postgres')
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

-- Tags table: Global read access, system write access
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY tags_read_policy ON tags
    FOR SELECT
    USING (true);

CREATE POLICY tags_system_write_policy ON tags
    FOR INSERT
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

CREATE POLICY tags_system_update_policy ON tags
    FOR UPDATE
    USING (current_setting('role') = 'service_role' OR current_user = 'postgres')
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

-- Clip tags table: Read access based on clip accessibility
ALTER TABLE clip_tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY clip_tags_read_policy ON clip_tags
    FOR SELECT
    USING (true); -- Tags are globally readable

CREATE POLICY clip_tags_system_write_policy ON clip_tags
    FOR INSERT
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

CREATE POLICY clip_tags_system_update_policy ON clip_tags
    FOR UPDATE
    USING (current_setting('role') = 'service_role' OR current_user = 'postgres')
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

CREATE POLICY clip_tags_system_delete_policy ON clip_tags
    FOR DELETE
    USING (current_setting('role') = 'service_role' OR current_user = 'postgres');

-- Jobs table: System managed only
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY jobs_system_policy ON jobs
    FOR ALL
    USING (current_setting('role') = 'service_role' OR current_user = 'postgres')
    WITH CHECK (current_setting('role') = 'service_role' OR current_user = 'postgres');

-- Create a security definer function to bypass RLS when needed by API
CREATE OR REPLACE FUNCTION bypass_rls_for_api()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- This function can be called by the API service role to temporarily bypass RLS
    -- for operations that need to work across users (like admin functions)
    PERFORM set_config('row_security', 'off', true);
END;
$$;

-- Grant execute permission to the service role
-- Note: This will be configured in Supabase after deployment
-- GRANT EXECUTE ON FUNCTION bypass_rls_for_api() TO service_role;

COMMIT; 