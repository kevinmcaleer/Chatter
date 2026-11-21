-- Migration: Add user_privacy for the public Liked list on kevsrobots profiles
-- Version: 021
-- Description: One row per user who changed a sharing default. likes_public
--              lets anyone see the projects that user liked.
-- Chatter's startup create_all also makes this table, so this is a safety net.

BEGIN;

CREATE TABLE IF NOT EXISTS user_privacy (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    likes_public BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Speeds up "what has this person liked, newest first".
CREATE INDEX IF NOT EXISTS ix_likes_user_id_created_at ON likes(user_id, created_at DESC);

INSERT INTO schema_version (version, description, applied_at)
VALUES (21, 'Add user_privacy (public Liked list)', NOW())
ON CONFLICT DO NOTHING;

COMMIT;
