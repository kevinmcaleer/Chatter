-- Migration 019: Rename tables from singular to plural naming convention
-- This migration aligns the database schema with the updated Chatter application code
-- Created: 2026-02-14

BEGIN;

-- Rename core tables to plural form
ALTER TABLE IF EXISTS "user" RENAME TO users;
ALTER TABLE IF EXISTS comment RENAME TO comments;
ALTER TABLE IF EXISTS "like" RENAME TO likes;
ALTER TABLE IF EXISTS pageview RENAME TO page_views;
ALTER TABLE IF EXISTS commentlike RENAME TO comment_likes;
ALTER TABLE IF EXISTS excluded_ip RENAME TO excluded_ips;
ALTER TABLE IF EXISTS commentversion RENAME TO comment_versions;

-- Rename project-related tables
ALTER TABLE IF EXISTS project_file RENAME TO project_files;
ALTER TABLE IF EXISTS project_step RENAME TO project_steps;
ALTER TABLE IF EXISTS project_image RENAME TO project_images;
ALTER TABLE IF EXISTS project_link RENAME TO project_links;
ALTER TABLE IF EXISTS project_tag RENAME TO project_tags;
ALTER TABLE IF EXISTS project_component RENAME TO project_components;

-- Rename other tables
ALTER TABLE IF EXISTS accountlog RENAME TO account_logs;

-- Update schema version
INSERT INTO schema_version (version, description, applied_at)
VALUES (19, 'Rename tables from singular to plural naming convention', NOW());

COMMIT;
