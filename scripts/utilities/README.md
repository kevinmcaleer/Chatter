# Utility Scripts

General-purpose utility scripts for data management and maintenance tasks.

## Purpose

These scripts handle data migrations, synchronization, and maintenance tasks for the Chatter application.

## Scripts

### Data Migration
- `migrate_profile_pictures_to_nas.py` - Migrates profile pictures from local container storage to NAS

### Data Maintenance
- `refresh_pageview_stats.py` - Refreshes materialized views for pageview statistics
- `add_test_comments.py` - Adds test comment data for development/testing

## Usage

### Profile Picture Migration

Migrates existing profile pictures from Docker containers to NAS storage.

```bash
# Run from development machine with SSH access to production servers
python scripts/utilities/migrate_profile_pictures_to_nas.py
```

**Requirements:**
- SSH access to production servers (dev01, dev03, dev04)
- NAS credentials configured in local .env
- Docker installed locally

**Process:**
1. Connects to each production server via SSH
2. Extracts files from `/tmp/chatter_uploads/profile_pictures` in containers
3. Uploads files to NAS (192.168.1.79/chatter/profile_pictures)
4. Verifies successful upload
5. Provides migration report

### Pageview Statistics Refresh

Refreshes the materialized view for pageview statistics.

```bash
# Refresh pageview stats
python scripts/utilities/refresh_pageview_stats.py

# In Docker container
docker exec chatter-app python scripts/utilities/refresh_pageview_stats.py
```

**When to run:**
- After bulk import of pageview data
- When pageview statistics appear outdated
- As part of regular maintenance (can be scheduled)

### Add Test Comments

Adds test comment data for development and testing purposes.

```bash
# Add test comments
python scripts/utilities/add_test_comments.py
```

**⚠️ Warning:** Only use in development/testing environments, not production!

## Scheduling Utilities

Some utilities can be scheduled for regular execution:

### Using Cron

```cron
# Refresh pageview stats every hour
0 * * * * docker exec chatter-app python scripts/utilities/refresh_pageview_stats.py

# Or on the host
0 * * * * cd /path/to/chatter && python scripts/utilities/refresh_pageview_stats.py
```

### Using Docker

Create a separate container or use docker-compose scheduled tasks:

```yaml
services:
  stats-refresh:
    image: chatter:latest
    command: python scripts/utilities/refresh_pageview_stats.py
    restart: "no"
    # Schedule using external orchestrator
```

## Development Guidelines

When creating new utility scripts:

1. **Location**: Place in `scripts/utilities/`
2. **Documentation**: Include docstrings and usage examples
3. **Error Handling**: Provide clear error messages
4. **Logging**: Log operations for troubleshooting
5. **Safety**: Include dry-run mode for potentially destructive operations
6. **Dependencies**: Document required packages in requirements.txt

## Best Practices

### Before Running Utilities

1. **Backup**: Always backup data before running utilities that modify data
2. **Test**: Test in development/staging environment first
3. **Verify**: Check database/storage state before and after
4. **Log**: Review logs for errors or warnings

### After Running Utilities

1. **Verify**: Confirm expected changes occurred
2. **Monitor**: Watch application behavior for issues
3. **Document**: Update relevant documentation if needed

## System Configuration

### Database Connection
- **Primary**: 192.168.2.3:5433
- **Database**: kevsrobots_cms
- **Credentials**: Configure via DATABASE_URL environment variable

### NAS Storage
- **Host**: 192.168.1.79
- **Share**: chatter
- **Credentials**: Configure via NAS_USERNAME and NAS_PASSWORD

## Guidelines

Per CLAUDE.md project guidelines:
- Utilities should be focused on specific tasks
- Utilities should have clear, descriptive names
- All database changes should be logged
- Utilities modifying data should support dry-run mode where appropriate
- Updates to requirements.txt should be made when new packages are added
