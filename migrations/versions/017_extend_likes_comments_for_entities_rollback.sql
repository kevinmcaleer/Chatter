-- Rollback Migration 017: Remove entity support from likes and comments

-- Drop unique indexes for entity-based likes
DROP INDEX IF EXISTS idx_like_user_entity;
DROP INDEX IF EXISTS idx_like_user_url;

-- Drop entity indexes
DROP INDEX IF EXISTS idx_like_entity;
DROP INDEX IF EXISTS idx_comment_entity;

-- Drop check constraints
ALTER TABLE "like" DROP CONSTRAINT IF EXISTS like_target_check;
ALTER TABLE comment DROP CONSTRAINT IF EXISTS comment_target_check;

-- Make url NOT NULL again
ALTER TABLE "like" ALTER COLUMN url SET NOT NULL;
ALTER TABLE comment ALTER COLUMN url SET NOT NULL;

-- Remove entity columns
ALTER TABLE "like" DROP COLUMN IF EXISTS entity_type;
ALTER TABLE "like" DROP COLUMN IF EXISTS entity_id;
ALTER TABLE comment DROP COLUMN IF EXISTS entity_type;
ALTER TABLE comment DROP COLUMN IF EXISTS entity_id;

-- Remove schema version entry
DELETE FROM schema_version WHERE version = 17;
