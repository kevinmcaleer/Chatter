-- Rollback Migration: Revert top_viewed_pages to use materialized view
-- Version: 012
-- Description: Restore the view to query from page_view_counts materialized view

DROP VIEW IF EXISTS top_viewed_pages;

CREATE OR REPLACE VIEW top_viewed_pages AS
SELECT
    url,
    view_count,
    unique_visitors,
    last_viewed_at
FROM page_view_counts
ORDER BY view_count DESC
LIMIT 10;

COMMENT ON VIEW top_viewed_pages IS 'Shows the top 10 most viewed pages ordered by view count';
