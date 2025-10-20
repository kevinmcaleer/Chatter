-- Rollback Migration: Add account management with logging
-- Date: 2025-10-20
-- Issue: #27

-- =====================================================
-- Rollback: Drop account_logs table
-- =====================================================

DROP INDEX IF EXISTS idx_account_logs_changed_at;
DROP INDEX IF EXISTS idx_account_logs_action;
DROP INDEX IF EXISTS idx_account_logs_changed_by;
DROP INDEX IF EXISTS idx_account_logs_user_id;

DROP TABLE IF EXISTS account_logs;

-- =====================================================
-- Rollback: Remove new fields from users table
-- =====================================================

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_status_check;

ALTER TABLE users DROP COLUMN IF EXISTS updated_at;
ALTER TABLE users DROP COLUMN IF EXISTS created_at;
ALTER TABLE users DROP COLUMN IF EXISTS type;
ALTER TABLE users DROP COLUMN IF EXISTS status;
ALTER TABLE users DROP COLUMN IF EXISTS date_of_birth;
ALTER TABLE users DROP COLUMN IF EXISTS lastname;
ALTER TABLE users DROP COLUMN IF EXISTS firstname;
