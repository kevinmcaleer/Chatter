#!/bin/bash
# Setup PostgreSQL automated backups to NAS
# Run this on the database server (192.168.2.3)

set -e

echo "========================================="
echo "PostgreSQL Backup Setup"
echo "========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

echo "1. Installing required packages..."
apt-get update -qq

# Try to install PostgreSQL client (version may vary by distro)
if ! apt-get install -y cifs-utils postgresql-client 2>/dev/null; then
    echo "Note: postgresql-client package not available, will use docker exec instead"
    apt-get install -y cifs-utils
fi

echo ""
echo "2. Creating mount point..."
mkdir -p /mnt/nas-backups

echo ""
echo "3. Creating NAS credentials file..."
cat > /root/.nas-credentials << 'EOF'
username=kev
password=Y3llowgirl28!
domain=WORKGROUP
EOF
chmod 600 /root/.nas-credentials

echo ""
echo "4. Testing NAS mount..."
if mount -t cifs //192.168.1.167/database /mnt/nas-backups -o credentials=/root/.nas-credentials,uid=1000,gid=1000; then
    echo "✓ NAS mounted successfully"
    ls -la /mnt/nas-backups
    umount /mnt/nas-backups
    echo "✓ NAS unmounted"
else
    echo "✗ NAS mount failed - please check NAS configuration"
    exit 1
fi

echo ""
echo "5. Creating backup script..."
cat > /usr/local/bin/postgres-backup.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

export PGHOST="192.168.2.3"
export PGPORT="5433"
export PGUSER="Hd4AZn:NlSpH"
export PGPASSWORD="8&0+6849Mx#S"

NAS_MOUNT="/mnt/nas-backups"
BACKUP_DIR="${NAS_MOUNT}/postgresql"
LOG_FILE="/var/log/postgres-backup.log"
DATE=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
DAY_OF_MONTH=$(date +%d)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "PostgreSQL Backup Started"
log "========================================="

if ! mountpoint -q "$NAS_MOUNT"; then
    log "Mounting NAS..."
    mount -t cifs //192.168.1.167/database "$NAS_MOUNT" -o credentials=/root/.nas-credentials,uid=1000,gid=1000
fi

mkdir -p "${BACKUP_DIR}/daily"
mkdir -p "${BACKUP_DIR}/weekly"
mkdir -p "${BACKUP_DIR}/monthly"

if [ "$DAY_OF_MONTH" = "01" ]; then
    BACKUP_TYPE="monthly"
    BACKUP_SUBDIR="${BACKUP_DIR}/monthly"
    RETENTION_DAYS=365
elif [ "$DAY_OF_WEEK" = "7" ]; then
    BACKUP_TYPE="weekly"
    BACKUP_SUBDIR="${BACKUP_DIR}/weekly"
    RETENTION_DAYS=28
else
    BACKUP_TYPE="daily"
    BACKUP_SUBDIR="${BACKUP_DIR}/daily"
    RETENTION_DAYS=7
fi

log "Backup type: ${BACKUP_TYPE}"

BACKUP_FILE="${BACKUP_SUBDIR}/all_databases_${BACKUP_TYPE}_${DATE}.sql"
log "Backing up all databases..."

# Try native pg_dumpall first, fallback to docker exec
if command -v pg_dumpall >/dev/null 2>&1; then
    log "Using native pg_dumpall"
    if pg_dumpall > "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        log "✓ Database backup completed"
    else
        log "✗ Database backup failed"
        exit 1
    fi
else
    log "Using docker exec for backup"
    CONTAINER=$(docker ps --filter name=postgres_primary -q | head -1)
    if [ -z "$CONTAINER" ]; then
        log "✗ ERROR: PostgreSQL container not found"
        exit 1
    fi
    if docker exec "$CONTAINER" pg_dumpall -U postgres > "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        log "✓ Database backup completed"
    else
        log "✗ Database backup failed"
        exit 1
    fi
fi

# Compress backup
gzip "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "✓ Backup compressed: ${BACKUP_SIZE}"

log "Cleaning up old ${BACKUP_TYPE} backups..."
find "${BACKUP_SUBDIR}" -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# Try to create symlink, but don't fail if CIFS doesn't support it
if ln -sf "$BACKUP_FILE" "${BACKUP_DIR}/latest_backup.sql.gz" 2>/dev/null; then
    log "✓ Created latest backup symlink"
else
    log "Note: Symlink not supported on CIFS share (not critical)"
fi

umount "$NAS_MOUNT" || log "WARNING: Failed to unmount NAS"

log "========================================="
log "Backup Completed: ${BACKUP_FILE}"
log "========================================="
EOFSCRIPT

chmod +x /usr/local/bin/postgres-backup.sh

echo ""
echo "6. Creating systemd service..."
cat > /etc/systemd/system/postgres-backup.service << 'EOF'
[Unit]
Description=PostgreSQL Backup to NAS
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/postgres-backup.sh
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "7. Creating systemd timer..."
cat > /etc/systemd/system/postgres-backup.timer << 'EOF'
[Unit]
Description=PostgreSQL Backup Timer
Requires=postgres-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo ""
echo "8. Enabling and starting timer..."
systemctl daemon-reload
systemctl enable postgres-backup.timer
systemctl start postgres-backup.timer

echo ""
echo "9. Running test backup..."
/usr/local/bin/postgres-backup.sh

echo ""
echo "========================================="
echo "✓ Backup Setup Complete!"
echo "========================================="
echo ""
echo "Backup schedule:"
echo "  Daily at 2:00 AM"
echo "  Retention: 7 days (daily), 28 days (weekly), 365 days (monthly)"
echo ""
echo "Check status:"
echo "  systemctl status postgres-backup.timer"
echo "  tail -50 /var/log/postgres-backup.log"
echo ""
echo "Manual backup:"
echo "  sudo /usr/local/bin/postgres-backup.sh"
echo ""
