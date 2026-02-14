-- Rollback Migration 019: Revert table names from plural to singular
-- This reverts the table naming changes if needed

BEGIN;

-- Revert core tables to singular form
ALTER TABLE IF EXISTS users RENAME TO "user";
ALTER TABLE IF EXISTS comments RENAME TO comment;
ALTER TABLE IF EXISTS likes RENAME TO "like";
ALTER TABLE IF EXISTS page_views RENAME TO pageview;
ALTER TABLE IF EXISTS comment_likes RENAME TO commentlike;
ALTER TABLE IF EXISTS excluded_ips RENAME TO excluded_ip;
ALTER TABLE IF EXISTS comment_versions RENAME TO commentversion;

-- Revert project-related tables
ALTER TABLE IF EXISTS project_files RENAME TO project_file;
ALTER TABLE IF EXISTS project_steps RENAME TO project_step;
ALTER TABLE IF EXISTS project_images RENAME TO project_image;
ALTER TABLE IF EXISTS project_links RENAME TO project_link;
ALTER TABLE IF EXISTS project_tags RENAME TO project_tag;
ALTER TABLE IF EXISTS project_components RENAME TO project_component;

-- Revert other tables
ALTER TABLE IF EXISTS account_logs RENAME TO accountlog;

-- Remove schema version entry
DELETE FROM schema_version WHERE version = 19;

COMMIT;
