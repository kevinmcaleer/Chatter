-- Rollback Migration 009: Remove comment editing and version history

-- Drop commentversion table
DROP TABLE IF EXISTS commentversion;

-- Remove edited_at column from comment table
ALTER TABLE comment DROP COLUMN IF EXISTS edited_at;
