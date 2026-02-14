-- Migration: Add account management with logging
-- Date: 2025-10-20
-- Issue: #27

-- =====================================================
-- Add new fields to users table for account management
-- =====================================================

-- Add new columns to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS firstname VARCHAR NOT NULL DEFAULT '';
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS lastname VARCHAR NOT NULL DEFAULT '';
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active';
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS type INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

-- Add constraints (drop first if exists to avoid errors)
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_status_check;
ALTER TABLE "user" ADD CONSTRAINT user_status_check CHECK (status IN ('active', 'inactive'));

-- Add comment to explain status values
COMMENT ON COLUMN "user".status IS 'User account status: active or inactive';
COMMENT ON COLUMN "user".type IS 'User type: 0 = regular user, 1 = admin';

-- =====================================================
-- Create account_logs table for comprehensive logging
-- =====================================================

CREATE TABLE IF NOT EXISTS accountlog (
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
    CONSTRAINT fk_accountlog_user_id
        FOREIGN KEY (user_id)
        REFERENCES "user"(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_accountlog_changed_by
        FOREIGN KEY (changed_by)
        REFERENCES "user"(id)
        ON DELETE SET NULL
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_accountlog_user_id ON accountlog(user_id);
CREATE INDEX IF NOT EXISTS idx_accountlog_changed_by ON accountlog(changed_by);
CREATE INDEX IF NOT EXISTS idx_accountlog_action ON accountlog(action);
CREATE INDEX IF NOT EXISTS idx_accountlog_changed_at ON accountlog(changed_at);

-- Add comments for documentation
COMMENT ON TABLE accountlog IS 'Comprehensive audit log for user account changes';
COMMENT ON COLUMN accountlog.action IS 'Type of action: created, updated, activated, deactivated, deleted';
COMMENT ON COLUMN accountlog.field_changed IS 'Specific field that was modified';
COMMENT ON COLUMN accountlog.old_value IS 'Previous value before change';
COMMENT ON COLUMN accountlog.new_value IS 'New value after change';
COMMENT ON COLUMN accountlog.changed_by IS 'User ID of who made the change';
COMMENT ON COLUMN accountlog.ip_address IS 'IP address of the request';
COMMENT ON COLUMN accountlog.user_agent IS 'Browser/client user agent string';
