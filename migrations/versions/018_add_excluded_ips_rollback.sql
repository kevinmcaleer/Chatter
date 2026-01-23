-- Rollback Migration: Remove excluded IPs table and restore original views
-- Version: 018
-- Description: Drop excluded_ip table and restore views without IP filtering

-- Drop the view first (depends on nothing now)
DROP VIEW IF EXISTS top_viewed_pages;

-- Drop the materialized view
DROP MATERIALIZED VIEW IF EXISTS page_view_counts;

-- Drop the excluded_ip table
DROP TABLE IF EXISTS excluded_ip;

-- Recreate original page_view_counts materialized view (without IP exclusion)
CREATE MATERIALIZED VIEW page_view_counts AS
SELECT
    url,
    COUNT(*) as view_count,
    COUNT(DISTINCT ip_address) as unique_visitors,
    MAX(viewed_at) as last_viewed_at
FROM pageview
GROUP BY url
ORDER BY view_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_page_view_counts_url ON page_view_counts(url);
COMMENT ON MATERIALIZED VIEW page_view_counts IS 'Aggregated page view statistics';

-- Recreate original top_viewed_pages view (without IP exclusion)
CREATE VIEW top_viewed_pages AS
SELECT
    url,
    COUNT(*) as view_count,
    COUNT(DISTINCT ip_address) as unique_visitors,
    MAX(viewed_at) as last_viewed_at
FROM pageview
GROUP BY url
ORDER BY view_count DESC
LIMIT 10;

COMMENT ON VIEW top_viewed_pages IS 'Shows the top 10 most viewed pages ordered by view count (real-time data from pageview table)';

-- Remove schema version entry
DELETE FROM schema_version WHERE version = 18;
