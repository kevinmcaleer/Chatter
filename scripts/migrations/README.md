# Migration Scripts

Database migration scripts and utilities for the Chatter project.

## Purpose

These scripts handle database schema changes, ensuring smooth deployment of database updates to production environments.

## Scripts

### Migration Application
- `apply_migrations.py` - Main migration application script
- `apply_migrations_simple.py` - Simplified migration runner
- `apply_migration_003.py` - Specific migration for version 003
- `apply_migration_011.py` - Specific migration for version 011
- `apply_migration_012.py` - Specific migration for version 012

### Migration Runners
- `run_migrations.py` - General migration runner
- `run_migrations_sqlalchemy.py` - SQLAlchemy-based migration runner
- `run_migrations_016_017.py` - Runs migrations 016 and 017
- `run_migration_013.py` - Specific migration for version 013
- `run_migration_013_simple.py` - Simplified version 013 runner

### Utilities
- `update_schema_version.py` - Updates the schema_version table
- `setup_production_db.sh` - Sets up production database

### Backup
- `apply_migrations.py.bak` - Backup of migration script

## Usage

### Applying Migrations

```bash
# General migration application
python scripts/migrations/apply_migrations.py

# Specific migration
python scripts/migrations/apply_migration_003.py

# In Docker container
docker exec chatter-app python scripts/migrations/apply_migrations.py
```

### Setting Up Production Database

```bash
bash scripts/migrations/setup_production_db.sh
```

## Guidelines

Per CLAUDE.md project guidelines:
- Database migrations should be documented in `design/migrations/`
- Migrations should always be able to rollback
- Migrations should update the schema_version table
- Migration SQL files are stored in `migrations/versions/`
- Database changes should be documented in `design/database.dbml`

## Migration Process

1. Write migration SQL in `migrations/versions/XXX_description.sql`
2. Write rollback SQL in `migrations/versions/XXX_description_rollback.sql`
3. Document the migration in `design/migrations/XXX_description.md`
4. Update `design/database.dbml` with schema changes
5. Test migration locally
6. Apply to production using scripts in this directory
7. Verify schema_version table is updated

## Connection Details

Migrations connect to the kevsrobots_cms database on:
- **Production Database**: 192.168.2.3:5433
- **Backup Database**: 192.168.2.4:5433

Credentials should be configured via environment variables or .env file.
