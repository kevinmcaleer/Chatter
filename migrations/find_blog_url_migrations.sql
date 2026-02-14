-- Find all blog/*.html URLs that might need migration to projects/*/
-- This helps identify other pages that may have the same issue

-- Find all comments with blog/*.html URLs
SELECT
    'comment' as table_name,
    url,
    COUNT(*) as count
FROM comment
WHERE url LIKE 'blog/%.html'
GROUP BY url
ORDER BY count DESC;

-- Find all likes with blog/*.html URLs
SELECT
    'like' as table_name,
    url,
    COUNT(*) as count
FROM "like"
WHERE url LIKE 'blog/%.html'
GROUP BY url
ORDER BY count DESC;

-- Find all page views with blog/*.html URLs
SELECT
    'pageview' as table_name,
    url,
    COUNT(*) as count
FROM pageview
WHERE url LIKE 'blog/%.html'
GROUP BY url
ORDER BY count DESC;
