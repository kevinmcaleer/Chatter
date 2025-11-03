-- Migration: Add comment like functionality (Issue #69)
-- Adds ability for users to like/upvote comments

-- Add like_count column to comment table
ALTER TABLE comment
ADD COLUMN IF NOT EXISTS like_count INTEGER DEFAULT 0;

-- Add index on like_count for efficient sorting by popularity
CREATE INDEX IF NOT EXISTS idx_comment_like_count ON comment(like_count);

-- Create commentlike table to track which users liked which comments
CREATE TABLE IF NOT EXISTS commentlike (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER NOT NULL REFERENCES comment(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_comment_user_like UNIQUE (comment_id, user_id)
);

-- Add indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_commentlike_comment_id ON commentlike(comment_id);
CREATE INDEX IF NOT EXISTS idx_commentlike_user_id ON commentlike(user_id);

-- Optional: Populate like_count from existing commentlike records (for re-running migration)
UPDATE comment
SET like_count = (
    SELECT COUNT(*)
    FROM commentlike
    WHERE commentlike.comment_id = comment.id
);

-- Verification queries (run after migration)
-- SELECT COUNT(*) as total_comment_likes FROM commentlike;
-- SELECT comment_id, COUNT(*) as likes FROM commentlike GROUP BY comment_id ORDER BY likes DESC LIMIT 10;
