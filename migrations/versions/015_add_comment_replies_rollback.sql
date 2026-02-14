-- Rollback: Remove comment reply/threading functionality (Issue #43)
-- Reverses migration 015_add_comment_replies.sql

-- Drop index
DROP INDEX IF EXISTS idx_comment_parent_comment_id;

-- Remove columns from comment table
ALTER TABLE comment DROP COLUMN IF EXISTS parent_comment_id;
ALTER TABLE comment DROP COLUMN IF EXISTS reply_count;
