-- Migration: Add force_password_reset flag for admin password reset capability
-- Date: 2025-10-23
-- Description: Allows admins to force users to reset password on next login

-- =====================================================
-- Add force_password_reset field to user table
-- =====================================================

ALTER TABLE user ADD COLUMN IF NOT EXISTS force_password_reset BOOLEAN DEFAULT FALSE;

-- Add index for efficient queries when checking login requirements
CREATE INDEX IF NOT EXISTS idx_user_force_password_reset ON user(force_password_reset);

-- Add comment for documentation
COMMENT ON COLUMN user.force_password_reset IS 'Flag to require user to reset password on next login (admin triggered)';
