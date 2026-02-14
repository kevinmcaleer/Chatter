-- Migration: Enhance comments table with moderation fields
-- Version: 007
-- Description: Add moderation fields for flagging, hiding, and reviewing comments

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_comment_url ON "comment"(url);
CREATE INDEX IF NOT EXISTS idx_comment_user_id ON "comment"(user_id);

-- Add moderation fields
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN DEFAULT FALSE;
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS flag_count INTEGER DEFAULT 0;
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS flag_reasons TEXT;
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE;
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS reviewed_by INTEGER REFERENCES "user"(id);

-- Add indexes for moderation queries
CREATE INDEX IF NOT EXISTS idx_comment_is_flagged ON "comment"(is_flagged) WHERE is_flagged = TRUE;
CREATE INDEX IF NOT EXISTS idx_comment_is_hidden ON "comment"(is_hidden) WHERE is_hidden = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN "comment".is_flagged IS 'Whether comment has been flagged for review';
COMMENT ON COLUMN "comment".flag_count IS 'Number of times comment has been reported';
COMMENT ON COLUMN "comment".flag_reasons IS 'JSON string of report reasons';
COMMENT ON COLUMN "comment".is_hidden IS 'Admin can hide abusive comments';
COMMENT ON COLUMN "comment".reviewed_at IS 'When admin reviewed the flagged comment';
COMMENT ON COLUMN "comment".reviewed_by IS 'Admin who reviewed the comment';
