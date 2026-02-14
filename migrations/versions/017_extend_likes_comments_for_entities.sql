-- Migration 017: Extend likes and comments to support entity-based system (projects, etc.)
-- This allows likes/comments on both URL-based content (blog posts) and entity-based content (projects)

-- Add entity columns to like table
ALTER TABLE "like"
    ADD COLUMN entity_type VARCHAR(50),
    ADD COLUMN entity_id INTEGER;

-- Add entity columns to comment table
ALTER TABLE comment
    ADD COLUMN entity_type VARCHAR(50),
    ADD COLUMN entity_id INTEGER;

-- Create indexes for entity-based lookups
CREATE INDEX idx_like_entity ON "like"(entity_type, entity_id) WHERE entity_type IS NOT NULL;
CREATE INDEX idx_comment_entity ON comment(entity_type, entity_id) WHERE entity_type IS NOT NULL;

-- Add check constraint to ensure either URL or entity is provided (but not both)
ALTER TABLE "like"
    ADD CONSTRAINT like_target_check CHECK (
        (url IS NOT NULL AND entity_type IS NULL AND entity_id IS NULL) OR
        (url IS NULL AND entity_type IS NOT NULL AND entity_id IS NOT NULL)
    );

ALTER TABLE comment
    ADD CONSTRAINT comment_target_check CHECK (
        (url IS NOT NULL AND entity_type IS NULL AND entity_id IS NULL) OR
        (url IS NULL AND entity_type IS NOT NULL AND entity_id IS NOT NULL)
    );

-- Update unique constraint for likes to include entity-based likes
-- First, drop old constraint if it exists (may not exist depending on how it was created)
-- Then create new unique index that handles both URL-based and entity-based likes
CREATE UNIQUE INDEX idx_like_user_url ON "like"(user_id, url) WHERE url IS NOT NULL;
CREATE UNIQUE INDEX idx_like_user_entity ON "like"(user_id, entity_type, entity_id) WHERE entity_type IS NOT NULL;

-- Make url column nullable since entity-based likes won't have URLs
ALTER TABLE "like" ALTER COLUMN url DROP NOT NULL;
ALTER TABLE comment ALTER COLUMN url DROP NOT NULL;

-- Update schema version
INSERT INTO schema_version (version, description, applied_at)
VALUES (17, 'Extend likes and comments for entity-based system (projects)', NOW());
