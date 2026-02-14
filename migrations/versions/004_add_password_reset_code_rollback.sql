-- Rollback Migration: Remove password reset code fields
-- Date: 2025-10-23
-- Description: Rollback changes from 004_add_password_reset_code.sql

-- =====================================================
-- Remove password reset code fields from user table
-- =====================================================

-- Drop index
DROP INDEX IF EXISTS idx_user_password_reset_code;

-- Drop columns
ALTER TABLE "user" DROP COLUMN IF EXISTS password_reset_code;
ALTER TABLE "user" DROP COLUMN IF EXISTS code_expires_at;
