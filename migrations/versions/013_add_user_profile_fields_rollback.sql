-- Rollback Migration 013: Remove user profile fields
-- Description: Remove profile picture, location, and bio fields

-- Remove profile fields from user table
ALTER TABLE "user" DROP COLUMN IF EXISTS profile_picture;
ALTER TABLE "user" DROP COLUMN IF EXISTS location;
ALTER TABLE "user" DROP COLUMN IF EXISTS bio;

-- Remove from schema_version
DELETE FROM schema_version WHERE version = 13;
