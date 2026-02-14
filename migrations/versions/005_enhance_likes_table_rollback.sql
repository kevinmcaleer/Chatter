-- Rollback Migration: Enhance likes table
-- Version: 005
-- Description: Rollback enhancements to likes table

-- Remove unique constraint
ALTER TABLE "like" DROP CONSTRAINT IF EXISTS unique_like_url_user;

-- Remove indexes
DROP INDEX IF EXISTS idx_like_url;
DROP INDEX IF EXISTS idx_like_user_id;

-- Remove created_at column
ALTER TABLE "like" DROP COLUMN IF EXISTS created_at;
