-- Rollback Migration 021: everyone's likes go back to private.
BEGIN;
DROP INDEX IF EXISTS ix_likes_user_id_created_at;
DROP TABLE IF EXISTS user_privacy;
DELETE FROM schema_version WHERE version = 21;
COMMIT;
