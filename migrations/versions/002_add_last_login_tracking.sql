-- Migration: Add last_login tracking for user engagement
-- Date: 2025-10-22
-- Issue: #30

-- =====================================================
-- Add last_login field to user table
-- =====================================================

ALTER TABLE user ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

-- Add index for efficient engagement queries
CREATE INDEX IF NOT EXISTS idx_user_last_login ON user(last_login);

-- Add comment for documentation
COMMENT ON COLUMN user.last_login IS 'Timestamp of last successful login for engagement tracking';
