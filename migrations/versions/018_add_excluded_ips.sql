-- Migration: Add excluded IPs table for analytics filtering
-- Version: 018
-- Description: Create table for IPs to exclude from analytics and update views

-- Create excluded_ip table
CREATE TABLE IF NOT EXISTS excluded_ip (
    id SERIAL PRIMARY KEY,
    ip_pattern VARCHAR NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add unique constraint on ip_pattern
CREATE UNIQUE INDEX IF NOT EXISTS idx_excluded_ip_pattern ON excluded_ip(ip_pattern);

-- Add comments for documentation
COMMENT ON TABLE excluded_ip IS 'IP addresses or patterns to exclude from page view analytics';
COMMENT ON COLUMN excluded_ip.ip_pattern IS 'IP address or CIDR pattern to exclude';
COMMENT ON COLUMN excluded_ip.description IS 'Reason for exclusion (e.g., developer, bot)';

-- Insert private IP ranges and known developer IPs
INSERT INTO excluded_ip (ip_pattern, description) VALUES
    ('192.168.%', 'Private network (Class C)'),
    ('10.%', 'Private network (Class A)'),
    ('172.16.%', 'Private network (Class B)'),
    ('172.17.%', 'Private network (Class B)'),
    ('172.18.%', 'Private network (Class B)'),
    ('172.19.%', 'Private network (Class B)'),
    ('172.20.%', 'Private network (Class B)'),
    ('172.21.%', 'Private network (Class B)'),
    ('172.22.%', 'Private network (Class B)'),
    ('172.23.%', 'Private network (Class B)'),
    ('172.24.%', 'Private network (Class B)'),
    ('172.25.%', 'Private network (Class B)'),
    ('172.26.%', 'Private network (Class B)'),
    ('172.27.%', 'Private network (Class B)'),
    ('172.28.%', 'Private network (Class B)'),
    ('172.29.%', 'Private network (Class B)'),
    ('172.30.%', 'Private network (Class B)'),
    ('172.31.%', 'Private network (Class B)'),
    ('127.%', 'Localhost'),
    ('81.130.193.208', 'Developer home IP')
ON CONFLICT (ip_pattern) DO NOTHING;

-- Drop and recreate page_view_counts materialized view to exclude IPs
DROP MATERIALIZED VIEW IF EXISTS page_view_counts CASCADE;

CREATE MATERIALIZED VIEW page_view_counts AS
SELECT
    url,
    COUNT(*) as view_count,
    COUNT(DISTINCT ip_address) as unique_visitors,
    MAX(viewed_at) as last_viewed_at
FROM pageview
WHERE NOT EXISTS (
    SELECT 1 FROM excluded_ip
    WHERE pageview.ip_address LIKE excluded_ip.ip_pattern
)
GROUP BY url
ORDER BY view_count DESC;

-- Recreate index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_page_view_counts_url ON page_view_counts(url);

-- Add comment
COMMENT ON MATERIALIZED VIEW page_view_counts IS 'Aggregated page view statistics (excludes IPs in excluded_ip table)';

-- Drop and recreate top_viewed_pages view
DROP VIEW IF EXISTS top_viewed_pages;

CREATE VIEW top_viewed_pages AS
SELECT
    url,
    COUNT(*) as view_count,
    COUNT(DISTINCT ip_address) as unique_visitors,
    MAX(viewed_at) as last_viewed_at
FROM pageview
WHERE NOT EXISTS (
    SELECT 1 FROM excluded_ip
    WHERE pageview.ip_address LIKE excluded_ip.ip_pattern
)
GROUP BY url
ORDER BY view_count DESC
LIMIT 10;

COMMENT ON VIEW top_viewed_pages IS 'Shows the top 10 most viewed pages (excludes IPs in excluded_ip table)';

-- Update schema version
INSERT INTO schema_version (version, description, applied_at)
VALUES (18, 'Add excluded IPs table for analytics filtering', CURRENT_TIMESTAMP);
