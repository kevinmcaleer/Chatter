-- Migration 010: Add soft delete fields for comment removal
-- Description: Add is_removed and removed_at fields to allow users to remove their own comments

-- Add is_removed column to comment table
ALTER TABLE comment ADD COLUMN IF NOT EXISTS is_removed BOOLEAN DEFAULT FALSE;

-- Add removed_at column to comment table
ALTER TABLE comment ADD COLUMN IF NOT EXISTS removed_at TIMESTAMP;

-- Create index on is_removed for efficient filtering
CREATE INDEX IF NOT EXISTS ix_comment_is_removed ON comment(is_removed);
