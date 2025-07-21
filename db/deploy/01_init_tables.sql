-- Deploy clipvault-schema:01_init_tables to pg
-- requires: 

BEGIN;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for additional crypto functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Clips table: Canonical record per link
CREATE TABLE clips (
    clip_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_url TEXT NOT NULL UNIQUE,
    media_type TEXT NOT NULL DEFAULT 'link' CHECK (media_type IN ('link', 'video', 'audio', 'image')),
    title TEXT,
    description TEXT,
    transcript TEXT,
    summary TEXT,
    thumbnail_url TEXT,
    duration_seconds INTEGER,
    word_count INTEGER,
    language_code TEXT DEFAULT 'en',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User clips table: Many-to-many join for user saves
CREATE TABLE user_clips (
    owner_uid UUID NOT NULL,
    clip_id UUID NOT NULL REFERENCES clips(clip_id) ON DELETE CASCADE,
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
    custom_tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    PRIMARY KEY (owner_uid, clip_id)
);

-- Tags table: Global tag catalog
CREATE TABLE tags (
    tag_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    color_hex TEXT DEFAULT '#6B7280',
    usage_count INTEGER NOT NULL DEFAULT 0,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Clip tags table: Tags per clip (many-to-many)
CREATE TABLE clip_tags (
    clip_id UUID NOT NULL REFERENCES clips(clip_id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    confidence_score FLOAT DEFAULT 1.0 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    added_by TEXT DEFAULT 'system' CHECK (added_by IN ('system', 'user', 'ai')),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (clip_id, tag_id)
);

-- Collections table: User folders/smart rules
CREATE TABLE collections (
    coll_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_uid UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_smart BOOLEAN NOT NULL DEFAULT FALSE,
    rule_json JSONB,
    color_hex TEXT DEFAULT '#6B7280',
    sort_order INTEGER DEFAULT 0,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- User can't have duplicate collection names
    UNIQUE (owner_uid, name)
);

-- Collections clips table: Collection membership (many-to-many)
CREATE TABLE collections_clips (
    coll_id UUID NOT NULL REFERENCES collections(coll_id) ON DELETE CASCADE,
    clip_id UUID NOT NULL REFERENCES clips(clip_id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    added_by_uid UUID, -- Who added this clip to the collection
    sort_order INTEGER DEFAULT 0,
    
    PRIMARY KEY (coll_id, clip_id)
);

-- Jobs table: AI processing status
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clip_id UUID NOT NULL REFERENCES clips(clip_id) ON DELETE CASCADE,
    job_type TEXT NOT NULL CHECK (job_type IN ('transcription', 'summarization', 'tagging', 'thumbnail')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    result_data JSONB,
    metadata JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to all tables with updated_at columns
CREATE TRIGGER update_clips_updated_at 
    BEFORE UPDATE ON clips 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tags_updated_at 
    BEFORE UPDATE ON tags 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collections_updated_at 
    BEFORE UPDATE ON collections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at 
    BEFORE UPDATE ON jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT; 