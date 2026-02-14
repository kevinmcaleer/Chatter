-- Migration: Enhance likes table with created_at, indexes, and unique constraint
-- Version: 005
-- Description: Add created_at timestamp, indexes on url and user_id, and unique constraint to prevent duplicate likes

-- Add created_at column if it doesn't exist
ALTER TABLE "like" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_like_url ON "like"(url);
CREATE INDEX IF NOT EXISTS idx_like_user_id ON "like"(user_id);

-- Add unique constraint to prevent duplicate likes (user can only like same URL once)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unique_like_url_user'
    ) THEN
        ALTER TABLE "like" ADD CONSTRAINT unique_like_url_user UNIQUE (url, user_id);
    END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN "like".created_at IS 'Timestamp when the like was created';
COMMENT ON INDEX idx_like_url IS 'Index for fast lookups by URL';
COMMENT ON INDEX idx_like_user_id IS 'Index for fast lookups by user_id';
COMMENT ON CONSTRAINT unique_like_url_user ON "like" IS 'Ensures user can only like the same URL once';
