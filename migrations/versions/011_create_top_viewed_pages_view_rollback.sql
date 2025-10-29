-- Rollback Migration: Drop top viewed pages view
-- Version: 011
-- Description: Remove the top_viewed_pages view

DROP VIEW IF EXISTS top_viewed_pages;
