-- Migration: Add comment reply/threading functionality (Issue #43)
-- Adds ability to reply to comments creating threaded conversations

-- Add parent_comment_id column to comment table (self-referencing foreign key)
ALTER TABLE comment
ADD COLUMN IF NOT EXISTS parent_comment_id INTEGER REFERENCES comment(id) ON DELETE CASCADE;

-- Add index on parent_comment_id for efficient lookups of replies
CREATE INDEX IF NOT EXISTS idx_comment_parent_comment_id ON comment(parent_comment_id);

-- Add reply_count column for denormalized reply counts
ALTER TABLE comment
ADD COLUMN IF NOT EXISTS reply_count INTEGER DEFAULT 0;

-- Populate reply_count from existing data (for re-running migration)
UPDATE comment
SET reply_count = (
    SELECT COUNT(*)
    FROM comment AS replies
    WHERE replies.parent_comment_id = comment.id
);

-- Verification queries (run after migration)
-- SELECT COUNT(*) as total_replies FROM comment WHERE parent_comment_id IS NOT NULL;
-- SELECT parent_comment_id, COUNT(*) as reply_count FROM comment WHERE parent_comment_id IS NOT NULL GROUP BY parent_comment_id ORDER BY reply_count DESC LIMIT 10;
