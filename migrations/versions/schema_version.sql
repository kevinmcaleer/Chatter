-- Migration version tracking table
-- This table tracks which migrations have been applied to the database

CREATE TABLE IF NOT EXISTS schema_version (
    id SERIAL PRIMARY KEY,
    version VARCHAR NOT NULL UNIQUE,
    description VARCHAR NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
    checksum VARCHAR
);

-- Add index for quick version lookups
CREATE INDEX IF NOT EXISTS idx_schema_version_version ON schema_version(version);

-- Add comment
COMMENT ON TABLE schema_version IS 'Tracks which database migrations have been applied';
COMMENT ON COLUMN schema_version.version IS 'Migration version number (e.g., 000, 001, 002)';
COMMENT ON COLUMN schema_version.description IS 'Human-readable description of what the migration does';
COMMENT ON COLUMN schema_version.checksum IS 'Optional checksum of the migration file for verification';
