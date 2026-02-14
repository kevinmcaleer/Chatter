-- Rollback Migration: Create view for most liked content
-- Version: 006
-- Description: Drop the most_liked_content materialized view

DROP MATERIALIZED VIEW IF EXISTS most_liked_content CASCADE;
