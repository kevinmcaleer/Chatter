-- Rollback Migration: Remove last_login tracking
-- Date: 2025-10-22
-- Issue: #30

-- =====================================================
-- Remove last_login field from user table
-- =====================================================

DROP INDEX IF EXISTS idx_user_last_login;

ALTER TABLE user DROP COLUMN IF EXISTS last_login;
