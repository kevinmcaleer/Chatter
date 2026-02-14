-- Migration: Create view for most liked content
-- Version: 006
-- Description: Create a materialized view that maintains a list of most liked elements

-- Create materialized view for most liked content
CREATE MATERIALIZED VIEW IF NOT EXISTS most_liked_content AS
SELECT
    url,
    COUNT(*) AS like_count,
    MAX(created_at) AS last_liked_at
FROM "like"
GROUP BY url
ORDER BY like_count DESC, last_liked_at DESC;

-- Create index on the materialized view for better performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_most_liked_content_url ON most_liked_content(url);

-- Add comment for documentation
COMMENT ON MATERIALIZED VIEW most_liked_content IS 'Aggregated view of content sorted by like count (highest to lowest)';
COMMENT ON COLUMN most_liked_content.url IS 'URL of the content';
COMMENT ON COLUMN most_liked_content.like_count IS 'Total number of likes for this content';
COMMENT ON COLUMN most_liked_content.last_liked_at IS 'Timestamp of the most recent like';

-- Note: This is a materialized view, so it needs to be refreshed periodically
-- You can refresh it with: REFRESH MATERIALIZED VIEW CONCURRENTLY most_liked_content;
