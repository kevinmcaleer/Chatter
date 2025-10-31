-- Migration 013: Add user profile fields
-- Description: Add profile picture, location, and bio fields for user profiles (Issue #44)

-- Add profile_picture column to user table
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS profile_picture VARCHAR;

-- Add location column to user table (for country/timezone info)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS location VARCHAR;

-- Add bio column to user table (short biography/about me)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS bio TEXT;

-- Update schema_version
INSERT INTO schema_version (version, description, applied_at)
VALUES (13, 'Add user profile fields (profile_picture, location, bio)', NOW());
