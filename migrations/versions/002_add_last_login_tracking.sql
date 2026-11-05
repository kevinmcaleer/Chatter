-- Migration: Add last_login tracking for user engagement
-- Date: 2025-10-22
-- Issue: #30

-- =====================================================
-- Add last_login field to user table
-- =====================================================

-- The table was renamed from "user" to "users"; "user" unquoted is a reserved
-- word in Postgres, so the original statements always failed. Work on
-- whichever table exists, and do nothing if the column is already there.
DO $$
DECLARE t text;
BEGIN
    IF to_regclass('public.users') IS NOT NULL THEN
        t := 'users';
    ELSIF to_regclass('public."user"') IS NOT NULL THEN
        t := 'user';
    ELSE
        RETURN;
    END IF;
    EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS last_login TIMESTAMP', t);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_user_last_login ON %I (last_login)', t);
    EXECUTE format('COMMENT ON COLUMN %I.last_login IS %L', t,
                   'Timestamp of last successful login for engagement tracking');
END $$;
