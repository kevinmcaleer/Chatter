-- Migration: Update comment and like URLs from old blog format to new projects format
-- This handles the Jekyll URL restructure where posts moved from /blog/*.html to /projects/*/

-- First, let's see what we're going to change (for verification)
-- SELECT url, COUNT(*) as count FROM comment WHERE url LIKE 'blog/%.html' GROUP BY url ORDER BY count DESC;

-- Update comments from blog/smars-q.html to projects/smars-q/
UPDATE comment
SET url = 'projects/smars-q/'
WHERE url = 'blog/smars-q.html';

-- Update likes from blog/smars-q.html to projects/smars-q/
UPDATE "like"
SET url = 'projects/smars-q/'
WHERE url = 'blog/smars-q.html';

-- Update page views from blog/smars-q.html to projects/smars-q/
UPDATE pageview
SET url = 'projects/smars-q/'
WHERE url = 'blog/smars-q.html';

-- Verification queries (run after migration)
-- SELECT 'Comments on projects/smars-q/' as type, COUNT(*) as count FROM comment WHERE url = 'projects/smars-q/'
-- UNION ALL
-- SELECT 'Likes on projects/smars-q/', COUNT(*) FROM "like" WHERE url = 'projects/smars-q/'
-- UNION ALL
-- SELECT 'Page views on projects/smars-q/', COUNT(*) FROM pageview WHERE url = 'projects/smars-q/';
