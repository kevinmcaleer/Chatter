-- Rollback Migration: Drop User Projects tables (Issue #15)
-- Description: Remove all project-related tables

-- Drop tables in reverse order of creation (respecting foreign key constraints)
DROP TABLE IF EXISTS tool_material CASCADE;
DROP TABLE IF EXISTS project_link CASCADE;
DROP TABLE IF EXISTS project_image CASCADE;
DROP TABLE IF EXISTS project_file CASCADE;
DROP TABLE IF EXISTS project_component CASCADE;
DROP TABLE IF EXISTS component CASCADE;
DROP TABLE IF EXISTS bill_of_material CASCADE;
DROP TABLE IF EXISTS project_step CASCADE;
DROP TABLE IF EXISTS project_tag CASCADE;
DROP TABLE IF EXISTS project CASCADE;

-- Remove from schema_version
DELETE FROM schema_version WHERE version = 16;
