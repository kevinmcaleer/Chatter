-- Rollback: Remove comment like functionality (Issue #69)
-- Reverses migration 014_add_comment_likes.sql

-- Drop commentlike table
DROP TABLE IF EXISTS commentlike;

-- Drop indexes
DROP INDEX IF EXISTS idx_comment_like_count;

-- Remove like_count column from comment table
ALTER TABLE comment DROP COLUMN IF EXISTS like_count;
