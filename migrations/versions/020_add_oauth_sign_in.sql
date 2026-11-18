-- Migration 020: Sign in with kevsrobots (OAuth 2 + PKCE) for apps outside .kevsrobots.com (#80)
-- Chatter also creates these tables (and seeds the snakie client) on startup, so running this by hand is optional.
-- Created: 2026-11-18

BEGIN;

CREATE TABLE IF NOT EXISTS oauth_clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    redirect_uris VARCHAR NOT NULL,   -- space-separated; a http://127.0.0.1/... entry allows any port
    scopes VARCHAR NOT NULL,          -- space-separated
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_codes (
    id SERIAL PRIMARY KEY,
    code_hash VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 of the code
    client_id VARCHAR(64) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope VARCHAR NOT NULL,
    code_challenge VARCHAR(128) NOT NULL,
    redirect_uri VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    grant_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_oauth_codes_user_id ON oauth_codes(user_id);

CREATE TABLE IF NOT EXISTS oauth_grants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id VARCHAR(64) NOT NULL,
    scope VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_oauth_grants_user_id ON oauth_grants(user_id);
CREATE INDEX IF NOT EXISTS ix_oauth_grants_client_id ON oauth_grants(client_id);

CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 of the refresh token
    grant_id INTEGER NOT NULL REFERENCES oauth_grants(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_oauth_refresh_tokens_grant_id ON oauth_refresh_tokens(grant_id);

-- created_at is given explicitly: if Chatter created the table on startup, the column has no database default.
INSERT INTO oauth_clients (client_id, name, redirect_uris, scopes, created_at) VALUES
    ('snakie', 'Snakie', 'https://app.snakie.org/auth/callback http://127.0.0.1/callback', 'profile projects:read projects:write', CURRENT_TIMESTAMP)
ON CONFLICT (client_id) DO NOTHING;

COMMIT;
