-- Migration: Create top viewed pages view
-- Version: 011
-- Description: Create a view that shows the top 10 most viewed pages

-- Create view for top 10 most viewed pages
CREATE OR REPLACE VIEW top_viewed_pages AS
SELECT
    url,
    view_count,
    unique_visitors,
    last_viewed_at
FROM page_view_counts
ORDER BY view_count DESC
LIMIT 10;

-- Add comment for documentation
COMMENT ON VIEW top_viewed_pages IS 'Shows the top 10 most viewed pages ordered by view count';
