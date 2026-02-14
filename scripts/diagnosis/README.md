# Diagnosis Scripts

Diagnostic and testing scripts for troubleshooting Chatter system components.

## Purpose

These scripts help diagnose issues with databases, network connections, storage systems, and application health.

## Scripts

### Database Diagnostics
- `test_db_connection.py` - Tests PostgreSQL database connectivity
- `check_comments.py` - Validates comment data and relationships
- `check_pageviews.py` - Checks pageview tracking functionality

### Storage Diagnostics
- `test_nas_connection.py` - Tests NAS (SMB/CIFS) connectivity and operations
- `check_and_migrate_local_files.py` - Checks and migrates files from local to NAS storage

### System Health Checks
- `diagnose_backend.sh` - Diagnoses backend application health
- `diagnose_jekyll_servers.sh` - Checks Jekyll frontend server status
- `check_cloudflare_health.sh` - Monitors Cloudflare tunnel health
- `monitor_jekyll_realtime.sh` - Real-time monitoring of Jekyll servers

### Troubleshooting
- `troubleshoot-db.sh` - General database troubleshooting script

## Usage

### Database Connection Test

```bash
# Test local database
python scripts/diagnosis/test_db_connection.py

# Test from Docker container
docker exec chatter-app python scripts/diagnosis/test_db_connection.py
```

### NAS Connection Test

```bash
# Test NAS connectivity
python scripts/diagnosis/test_nas_connection.py

# In Docker container
docker exec chatter-app python scripts/diagnosis/test_nas_connection.py
```

### System Health Checks

```bash
# Check backend health
bash scripts/diagnosis/diagnose_backend.sh

# Check Jekyll servers
bash scripts/diagnosis/diagnose_jekyll_servers.sh

# Monitor Cloudflare tunnel
bash scripts/diagnosis/check_cloudflare_health.sh

# Real-time Jekyll monitoring
bash scripts/diagnosis/monitor_jekyll_realtime.sh
```

### Data Validation

```bash
# Check comments
python scripts/diagnosis/check_comments.py

# Check pageviews
python scripts/diagnosis/check_pageviews.py

# Check and migrate local files
python scripts/diagnosis/check_and_migrate_local_files.py
```

## System Architecture

### Servers
- **Frontend (Jekyll)**: 192.168.2.1, 192.168.2.2
- **Database Primary**: 192.168.2.3:5433
- **Database Backup**: 192.168.2.4:5433
- **NAS Storage**: 192.168.1.79 (SMB share: chatter)

### Docker Registry
- **Local Registry**: 192.168.2.1:5000

## Troubleshooting Common Issues

### Database Connection Issues
1. Run `scripts/diagnosis/test_db_connection.py`
2. Check database server is running: `pg_isready -h 192.168.2.3 -p 5433`
3. Verify credentials in .env file
4. Check network connectivity to database servers

### NAS Storage Issues
1. Run `scripts/diagnosis/test_nas_connection.py`
2. Verify NAS_HOST, NAS_USERNAME, NAS_PASSWORD in .env
3. Check SMB share is accessible: `smbclient //192.168.1.79/chatter -U kevsrobots`
4. System falls back to local storage if NAS unavailable

### Backend Health Issues
1. Run `scripts/diagnosis/diagnose_backend.sh`
2. Check application logs: `docker logs chatter-app`
3. Verify health endpoint: `curl http://localhost:8000/health`
4. Check database connections and migrations

### Jekyll Server Issues
1. Run `scripts/diagnosis/diagnose_jekyll_servers.sh`
2. Monitor real-time: `scripts/diagnosis/monitor_jekyll_realtime.sh`
3. Check Cloudflare: `scripts/diagnosis/check_cloudflare_health.sh`
4. Verify servers at 192.168.2.1 and 192.168.2.2

## Guidelines

Per CLAUDE.md project guidelines:
- Diagnosis scripts should be stored in `scripts/diagnosis/`
- Scripts should provide clear, actionable output
- Scripts should not modify data (read-only diagnostics)
- Use these scripts proactively for monitoring and troubleshooting
