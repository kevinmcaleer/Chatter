-- Rollback Migration: Remove force_password_reset flag
-- Date: 2025-10-23
-- Description: Rollback changes from 003_add_force_password_reset.sql

-- =====================================================
-- Remove force_password_reset field from user table
-- =====================================================

-- Drop index
DROP INDEX IF EXISTS idx_user_force_password_reset;

-- Drop column
ALTER TABLE user DROP COLUMN IF EXISTS force_password_reset;
