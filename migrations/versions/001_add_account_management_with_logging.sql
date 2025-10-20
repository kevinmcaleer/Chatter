-- Migration: Add account management with logging
-- Date: 2025-10-20
-- Issue: #27

-- =====================================================
-- Add new fields to users table for account management
-- =====================================================

-- Add new columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS firstname VARCHAR NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS lastname VARCHAR NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS type INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

-- Add constraints
ALTER TABLE users ADD CONSTRAINT users_status_check CHECK (status IN ('active', 'inactive'));

-- Add comment to explain status values
COMMENT ON COLUMN users.status IS 'User account status: active or inactive';
COMMENT ON COLUMN users.type IS 'User type: 0 = regular user, 1 = admin';

-- =====================================================
-- Create account_logs table for comprehensive logging
-- =====================================================

CREATE TABLE IF NOT EXISTS account_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    action VARCHAR NOT NULL,
    field_changed VARCHAR,
    old_value VARCHAR,
    new_value VARCHAR,
    changed_by INTEGER,
    changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR,
    user_agent VARCHAR,

    -- Foreign key constraints
    CONSTRAINT fk_account_logs_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_account_logs_changed_by
        FOREIGN KEY (changed_by)
        REFERENCES users(id)
        ON DELETE SET NULL
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_account_logs_user_id ON account_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_account_logs_changed_by ON account_logs(changed_by);
CREATE INDEX IF NOT EXISTS idx_account_logs_action ON account_logs(action);
CREATE INDEX IF NOT EXISTS idx_account_logs_changed_at ON account_logs(changed_at);

-- Add comments for documentation
COMMENT ON TABLE account_logs IS 'Comprehensive audit log for user account changes';
COMMENT ON COLUMN account_logs.action IS 'Type of action: created, updated, activated, deactivated, deleted';
COMMENT ON COLUMN account_logs.field_changed IS 'Specific field that was modified';
COMMENT ON COLUMN account_logs.old_value IS 'Previous value before change';
COMMENT ON COLUMN account_logs.new_value IS 'New value after change';
COMMENT ON COLUMN account_logs.changed_by IS 'User ID of who made the change';
COMMENT ON COLUMN account_logs.ip_address IS 'IP address of the request';
COMMENT ON COLUMN account_logs.user_agent IS 'Browser/client user agent string';
