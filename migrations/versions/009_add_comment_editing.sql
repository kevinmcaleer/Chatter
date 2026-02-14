-- Migration 009: Add comment editing and version history
-- Description: Add edited_at field to comment table and create commentversion table

-- Add edited_at column to comment table
ALTER TABLE comment ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP;

-- Create commentversion table for edit history
CREATE TABLE IF NOT EXISTS commentversion (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER NOT NULL REFERENCES comment(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    edited_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    CONSTRAINT fk_commentversion_comment FOREIGN KEY (comment_id) REFERENCES comment(id) ON DELETE CASCADE
);

-- Create index on comment_id for fast lookups
CREATE INDEX IF NOT EXISTS ix_commentversion_comment_id ON commentversion(comment_id);

-- Create index on edited_at for sorting by version
CREATE INDEX IF NOT EXISTS ix_commentversion_edited_at ON commentversion(edited_at);
