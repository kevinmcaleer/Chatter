-- Rollback Migration: Drop page_view table
-- Version: 008
-- Description: Remove page view tracking

-- Drop materialized view and indexes
DROP INDEX IF EXISTS idx_page_view_counts_url;
DROP MATERIALIZED VIEW IF EXISTS page_view_counts;

-- Drop indexes
DROP INDEX IF EXISTS idx_pageview_viewed_at;
DROP INDEX IF EXISTS idx_pageview_ip_address;
DROP INDEX IF EXISTS idx_pageview_url;

-- Drop table
DROP TABLE IF EXISTS pageview;
