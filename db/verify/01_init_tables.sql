-- Verify clipvault-schema:01_init_tables on pg

BEGIN;

-- Verify extensions exist
SELECT 1/COUNT(*) FROM pg_extension WHERE extname = 'uuid-ossp';
SELECT 1/COUNT(*) FROM pg_extension WHERE extname = 'pgcrypto';
SELECT 1/COUNT(*) FROM pg_extension WHERE extname = 'pg_trgm';

-- Verify all tables exist
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'clips';
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'user_clips';
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'tags';
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'clip_tags';
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'collections';
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'collections_clips';
SELECT 1/COUNT(*) FROM information_schema.tables WHERE table_name = 'jobs';

-- Verify primary keys exist
SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'clips' AND constraint_type = 'PRIMARY KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'user_clips' AND constraint_type = 'PRIMARY KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'tags' AND constraint_type = 'PRIMARY KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'clip_tags' AND constraint_type = 'PRIMARY KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'collections' AND constraint_type = 'PRIMARY KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'collections_clips' AND constraint_type = 'PRIMARY KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'jobs' AND constraint_type = 'PRIMARY KEY';

-- Verify unique constraints
SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'clips' AND constraint_type = 'UNIQUE' AND constraint_name LIKE '%source_url%';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'tags' AND constraint_type = 'UNIQUE' AND constraint_name LIKE '%name%';

-- Verify foreign keys exist
SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'user_clips' AND constraint_type = 'FOREIGN KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'clip_tags' AND constraint_type = 'FOREIGN KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'collections_clips' AND constraint_type = 'FOREIGN KEY';

SELECT 1/COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'jobs' AND constraint_type = 'FOREIGN KEY';

-- Verify trigger function exists
SELECT 1/COUNT(*) FROM information_schema.routines 
WHERE routine_name = 'update_updated_at_column';

-- Verify triggers exist
SELECT 1/COUNT(*) FROM information_schema.triggers 
WHERE trigger_name = 'update_clips_updated_at';

SELECT 1/COUNT(*) FROM information_schema.triggers 
WHERE trigger_name = 'update_tags_updated_at';

SELECT 1/COUNT(*) FROM information_schema.triggers 
WHERE trigger_name = 'update_collections_updated_at';

SELECT 1/COUNT(*) FROM information_schema.triggers 
WHERE trigger_name = 'update_jobs_updated_at';

ROLLBACK; 