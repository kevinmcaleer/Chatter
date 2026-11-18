-- Rollback Migration 020: remove Sign in with kevsrobots tables (#80). Signs every app out.
BEGIN;
DROP TABLE IF EXISTS oauth_refresh_tokens;
DROP TABLE IF EXISTS oauth_grants;
DROP TABLE IF EXISTS oauth_codes;
DROP TABLE IF EXISTS oauth_clients;
COMMIT;
