-- Migration: Fix top viewed pages view to always be current
-- Version: 012
-- Description: Recreate top_viewed_pages to query directly from pageview table instead of materialized view

-- Drop the old view
DROP VIEW IF EXISTS top_viewed_pages;

-- Create view that queries directly from pageview table for real-time data
CREATE OR REPLACE VIEW top_viewed_pages AS
SELECT
    url,
    COUNT(*) as view_count,
    COUNT(DISTINCT ip_address) as unique_visitors,
    MAX(viewed_at) as last_viewed_at
FROM pageview
GROUP BY url
ORDER BY view_count DESC
LIMIT 10;

-- Add comment for documentation
COMMENT ON VIEW top_viewed_pages IS 'Shows the top 10 most viewed pages ordered by view count (real-time data from pageview table)';
