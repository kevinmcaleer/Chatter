# URL Migration Scripts

## Problem

When Jekyll post URLs are restructured (e.g., from `/blog/*.html` to `/projects/*/`), comments, likes, and page views remain associated with the old URL. This causes:

- Comments not appearing on the new URL
- Like counts being split between old and new URLs
- Page view statistics being fragmented

## Solution

Use the SQL migration scripts in this directory to update URLs in the database.

## Step 1: Find URLs that need migration

First, identify which blog URLs have comments, likes, or page views:

```bash
docker exec chatter-app psql postgresql://kevsrobots_user:ChangeMe123@192.168.2.1:5433/kevsrobots_cms -f /app/migrations/find_blog_url_migrations.sql
```

This will show all `blog/*.html` URLs with activity.

## Step 2: Update migration script

Edit `migrate_blog_urls.sql` to add UPDATE statements for each URL that needs migrating.

For example, if you find `blog/my-robot.html` should become `projects/my-robot/`:

```sql
UPDATE comment SET url = 'projects/my-robot/' WHERE url = 'blog/my-robot.html';
UPDATE "like" SET url = 'projects/my-robot/' WHERE url = 'blog/my-robot.html';
UPDATE pageview SET url = 'projects/my-robot/' WHERE url = 'blog/my-robot.html';
```

## Step 3: Run the migration

```bash
docker exec chatter-app psql postgresql://kevsrobots_user:ChangeMe123@192.168.2.1:5433/kevsrobots_cms -f /app/migrations/migrate_blog_urls.sql
```

## Step 4: Verify

Check that the comments now appear on the new URL:

```bash
curl -s "https://chatter.kevsrobots.com/interact/comments/projects/smars-q/" | python3 -m json.tool
```

## Current Migrations

### SMARS Q: blog/smars-q.html → projects/smars-q/

- **8 comments** being migrated
- **Status**: Ready to run

Run with:

```bash
docker exec chatter-app psql postgresql://kevsrobots_user:ChangeMe123@192.168.2.1:5433/kevsrobots_cms -f /app/migrations/migrate_blog_urls.sql
```

## Future Prevention

Consider implementing URL aliasing or redirects at the application level so old URLs automatically map to new ones. This would require:

1. A `url_aliases` table mapping old → new URLs
2. Middleware to check aliases before querying comments/likes/pageviews
3. Or: Update Jekyll to maintain consistent URLs with redirects

## Notes

- Always backup the database before running migrations
- Test migrations on dev environment first
- The migration updates data in-place (no rollback unless you have backups)
- After migration, the old URLs will have 0 comments/likes/views
