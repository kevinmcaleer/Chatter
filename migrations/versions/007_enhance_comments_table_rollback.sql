-- Rollback Migration: Enhance comments table
-- Version: 007
-- Description: Rollback comment moderation enhancements

-- Remove indexes
DROP INDEX IF EXISTS idx_comment_url;
DROP INDEX IF EXISTS idx_comment_user_id;
DROP INDEX IF EXISTS idx_comment_is_flagged;
DROP INDEX IF EXISTS idx_comment_is_hidden;

-- Remove columns
ALTER TABLE "comment" DROP COLUMN IF EXISTS is_flagged;
ALTER TABLE "comment" DROP COLUMN IF EXISTS flag_count;
ALTER TABLE "comment" DROP COLUMN IF EXISTS flag_reasons;
ALTER TABLE "comment" DROP COLUMN IF EXISTS is_hidden;
ALTER TABLE "comment" DROP COLUMN IF EXISTS reviewed_at;
ALTER TABLE "comment" DROP COLUMN IF EXISTS reviewed_by;
