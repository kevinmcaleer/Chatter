-- Migration: Create page_view table
-- Version: 008
-- Description: Add page view tracking for analytics

-- Create page_view table
CREATE TABLE IF NOT EXISTS pageview (
    id SERIAL PRIMARY KEY,
    url VARCHAR NOT NULL,
    ip_address VARCHAR NOT NULL,
    viewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT
);

-- Add indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_pageview_url ON pageview(url);
CREATE INDEX IF NOT EXISTS idx_pageview_ip_address ON pageview(ip_address);
CREATE INDEX IF NOT EXISTS idx_pageview_viewed_at ON pageview(viewed_at);

-- Add comments for documentation
COMMENT ON TABLE pageview IS 'Tracks page views for analytics';
COMMENT ON COLUMN pageview.url IS 'Page URL that was viewed';
COMMENT ON COLUMN pageview.ip_address IS 'IP address of the visitor';
COMMENT ON COLUMN pageview.viewed_at IS 'Timestamp when page was viewed';
COMMENT ON COLUMN pageview.user_agent IS 'Browser/device information';

-- Create materialized view for page view counts
CREATE MATERIALIZED VIEW IF NOT EXISTS page_view_counts AS
SELECT
    url,
    COUNT(*) as view_count,
    COUNT(DISTINCT ip_address) as unique_visitors,
    MAX(viewed_at) as last_viewed_at
FROM pageview
GROUP BY url
ORDER BY view_count DESC;

-- Add index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_page_view_counts_url ON page_view_counts(url);

-- Add comments
COMMENT ON MATERIALIZED VIEW page_view_counts IS 'Aggregated page view statistics';
