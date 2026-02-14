# Scripts Directory

This directory contains all utility and maintenance scripts for the Chatter project, organized by purpose.

## Directory Structure

### migrations/
Database migration scripts and utilities for applying schema changes to the production database.

**Contains:**
- Migration application scripts (apply_migration_*.py, run_migrations*.py)
- Schema version management utilities
- Database setup scripts

**Usage:** See `migrations/README.md` for details

### diagnosis/
Diagnostic and testing scripts for troubleshooting system components.

**Contains:**
- Database connection tests
- NAS connectivity tests
- System health checks
- Monitoring scripts

**Usage:** See `diagnosis/README.md` for details

### utilities/
General-purpose utility scripts for data management and maintenance tasks.

**Contains:**
- Data migration utilities
- Data refresh/sync scripts
- Maintenance scripts

**Usage:** See `utilities/README.md` for details

## Guidelines

Per CLAUDE.md project guidelines:
- All migration scripts should be in `scripts/migrations/`
- All diagnosis scripts should be in `scripts/diagnosis/`
- Scripts should be well-documented and include usage examples
- Database migrations should always be documented in `design/migrations/`
- Database migration documentation should describe the change, provide rollback steps, and update schema_version
