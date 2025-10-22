-- Migration: Create initial database schema
-- Date: 2025-10-22
-- Description: Creates all tables from scratch for fresh PostgreSQL database

-- =====================================================
-- Create user table with all fields
-- =====================================================

CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    firstname VARCHAR NOT NULL DEFAULT '',
    lastname VARCHAR NOT NULL DEFAULT '',
    date_of_birth DATE,
    status VARCHAR NOT NULL DEFAULT 'active',
    type INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,

    CONSTRAINT user_status_check CHECK (status IN ('active', 'inactive'))
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);
CREATE INDEX IF NOT EXISTS idx_user_last_login ON "user"(last_login);

-- Add comments
COMMENT ON TABLE "user" IS 'User accounts with authentication and profile information';
COMMENT ON COLUMN "user".status IS 'User account status: active or inactive';
COMMENT ON COLUMN "user".type IS 'User type: 0 = regular user, 1 = admin';
COMMENT ON COLUMN "user".last_login IS 'Timestamp of last successful login for engagement tracking';

-- =====================================================
-- Create accountlog table for comprehensive logging
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

-- =====================================================
-- Create like table
-- =====================================================

CREATE TABLE IF NOT EXISTS "like" (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    url VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_like_user_id
        FOREIGN KEY (user_id)
        REFERENCES "user"(id)
        ON DELETE CASCADE,

    -- Ensure a user can only like a URL once
    CONSTRAINT unique_user_url_like UNIQUE (user_id, url)
);

CREATE INDEX IF NOT EXISTS idx_like_user_id ON "like"(user_id);
CREATE INDEX IF NOT EXISTS idx_like_url ON "like"(url);

COMMENT ON TABLE "like" IS 'User likes for content URLs';

-- =====================================================
-- Create comment table
-- =====================================================

CREATE TABLE IF NOT EXISTS comment (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    url VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_comment_user_id
        FOREIGN KEY (user_id)
        REFERENCES "user"(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comment_user_id ON comment(user_id);
CREATE INDEX IF NOT EXISTS idx_comment_url ON comment(url);
CREATE INDEX IF NOT EXISTS idx_comment_created_at ON comment(created_at);

COMMENT ON TABLE comment IS 'User comments on content URLs';
