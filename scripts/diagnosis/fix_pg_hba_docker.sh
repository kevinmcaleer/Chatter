#!/bin/bash
# Fix PostgreSQL pg_hba.conf on Docker-based database server
# Run this ON the database server (192.168.2.3)

set -e

echo "========================================="
echo "PostgreSQL Docker Configuration Fix"
echo "Database Server: 192.168.2.3"
echo "========================================="
echo ""

# PostgreSQL credentials
PG_USERNAME="Hd4AZn:NlSpH"
PG_PASSWORD="8&0+6849Mx#S"
PG_DATABASE="kevsrobots_cms"
PG_PORT="5433"

# Find PostgreSQL container
CONTAINER=$(docker ps --filter name=postgres -q | head -1)

if [ -z "$CONTAINER" ]; then
    echo "Error: No PostgreSQL container found"
    echo "Looking for containers..."
    docker ps
    exit 1
fi

echo "PostgreSQL container: $CONTAINER"
echo ""

# Backup directory
BACKUP_DIR="/var/backups/postgresql"
sudo mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "==================================================================="
echo "Step 1: Backing up configuration files..."
echo "==================================================================="
docker cp "${CONTAINER}:/var/lib/postgresql/data/pg_hba.conf" "${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP}"
docker cp "${CONTAINER}:/var/lib/postgresql/data/postgresql.conf" "${BACKUP_DIR}/postgresql.conf.backup.${TIMESTAMP}"
echo "✓ Backups created in $BACKUP_DIR"

echo ""
echo "==================================================================="
echo "Step 2: Checking if PostgreSQL user exists..."
echo "==================================================================="

# Check if user exists (connect as postgres superuser inside container)
USER_EXISTS=$(docker exec $CONTAINER psql -U postgres -p $PG_PORT -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USERNAME'" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" = "1" ]; then
    echo "✓ User '$PG_USERNAME' exists"
else
    echo "Creating user '$PG_USERNAME'..."
    docker exec $CONTAINER psql -U postgres -p $PG_PORT << EOF
CREATE USER "$PG_USERNAME" WITH PASSWORD '$PG_PASSWORD';
EOF
    echo "✓ User '$PG_USERNAME' created"
fi

echo ""
echo "==================================================================="
echo "Step 3: Setting user password..."
echo "==================================================================="
docker exec $CONTAINER psql -U postgres -p $PG_PORT -c "ALTER USER \"$PG_USERNAME\" WITH PASSWORD '$PG_PASSWORD';" > /dev/null
echo "✓ Password set for user '$PG_USERNAME'"

echo ""
echo "==================================================================="
echo "Step 4: Granting database permissions..."
echo "==================================================================="

# First grant database-level permissions
docker exec $CONTAINER psql -U postgres -p $PG_PORT -c "GRANT ALL PRIVILEGES ON DATABASE $PG_DATABASE TO \"$PG_USERNAME\";" > /dev/null

# Then grant schema-level permissions
docker exec $CONTAINER psql -U postgres -p $PG_PORT -d $PG_DATABASE << EOF
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO "$PG_USERNAME";
EOF
echo "✓ All permissions granted to user '$PG_USERNAME'"

echo ""
echo "==================================================================="
echo "Step 5: Creating new pg_hba.conf..."
echo "==================================================================="

cat > /tmp/pg_hba.conf << 'EOF'
# PostgreSQL Client Authentication Configuration File
# ===================================================
# Database rebuilt on 2026-02-14 after disk failure
# Configuration for Chatter application

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             postgres                                trust
local   all             all                                     peer

# IPv4 local connections:
host    all             postgres        127.0.0.1/32            trust

# ===================================================
# CHATTER APPLICATION ACCESS
# Username: Hd4AZn:NlSpH (contains colon - must be quoted!)
# Allow Chatter servers to connect to kevsrobots_cms database
# ===================================================
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.1/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.2/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.3/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.4/32          md5

# Allow entire 192.168.2.0/24 subnet (alternative)
# host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.0/24          md5

# IPv4 local connections (other users)
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
EOF

# Copy to container
docker cp /tmp/pg_hba.conf "${CONTAINER}:/var/lib/postgresql/data/pg_hba.conf"
docker exec $CONTAINER chown postgres:postgres /var/lib/postgresql/data/pg_hba.conf
docker exec $CONTAINER chmod 640 /var/lib/postgresql/data/pg_hba.conf
echo "✓ pg_hba.conf updated"

echo ""
echo "==================================================================="
echo "Step 6: Checking postgresql.conf listen_addresses..."
echo "==================================================================="

CURRENT_LISTEN=$(docker exec $CONTAINER grep "^listen_addresses" /var/lib/postgresql/data/postgresql.conf || echo "")

if echo "$CURRENT_LISTEN" | grep -q "listen_addresses.*=.*'\\*'"; then
    echo "✓ listen_addresses already set to '*'"
else
    echo "Setting listen_addresses to '*'..."
    docker exec $CONTAINER sh -c "sed -i \"s/^#*listen_addresses.*/listen_addresses = '*'/\" /var/lib/postgresql/data/postgresql.conf"

    # If it wasn't found, append it
    if ! docker exec $CONTAINER grep -q "^listen_addresses" /var/lib/postgresql/data/postgresql.conf; then
        docker exec $CONTAINER sh -c "echo \"listen_addresses = '*'\" >> /var/lib/postgresql/data/postgresql.conf"
    fi
    echo "✓ listen_addresses updated"
fi

echo ""
echo "==================================================================="
echo "Step 7: Reloading PostgreSQL configuration..."
echo "==================================================================="

# Reload configuration (send SIGHUP to postgres process)
docker exec $CONTAINER psql -U postgres -p $PG_PORT -c "SELECT pg_reload_conf();" > /dev/null
echo "✓ PostgreSQL configuration reloaded"

# Wait a moment for reload to take effect
sleep 2

echo ""
echo "==================================================================="
echo "Step 8: Testing configuration..."
echo "==================================================================="

# Test connection from inside container
echo -n "Testing connection from inside container... "
if docker exec -e PGPASSWORD="$PG_PASSWORD" $CONTAINER psql -h localhost -p $PG_PORT -U "$PG_USERNAME" -d "$PG_DATABASE" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
    echo "Checking PostgreSQL logs..."
    docker logs --tail 20 $CONTAINER
fi

# Test connection from host (if psql is installed)
if command -v psql &> /dev/null; then
    echo -n "Testing connection from host (192.168.2.3)... "
    if PGPASSWORD="$PG_PASSWORD" psql -h 192.168.2.3 -p $PG_PORT -U "$PG_USERNAME" -d "$PG_DATABASE" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✓ SUCCESS"
    else
        echo "✗ FAILED (may need to restart container)"
    fi
else
    echo "⚠ psql not installed on host, skipping external test"
fi

echo ""
echo "==================================================================="
echo "Configuration Complete!"
echo "==================================================================="
echo ""
echo "Database server details:"
echo "  Host: 192.168.2.3"
echo "  Port: $PG_PORT"
echo "  Database: $PG_DATABASE"
echo "  Username: $PG_USERNAME"
echo "  Container: $CONTAINER"
echo ""
echo "Allowed client IPs:"
echo "  - 192.168.2.1 (Chatter server)"
echo "  - 192.168.2.2 (Chatter server)"
echo "  - 192.168.2.3 (Database server)"
echo "  - 192.168.2.4 (Backup server)"
echo ""
echo "Backups saved to: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Test connection from Chatter server:"
echo "   ssh kev@192.168.2.2"
echo "   PGPASSWORD='$PG_PASSWORD' psql -h 192.168.2.3 -p $PG_PORT -U '$PG_USERNAME' -d $PG_DATABASE -c 'SELECT version();'"
echo ""
echo "2. If test fails, restart the PostgreSQL container:"
echo "   docker restart $CONTAINER"
echo ""
echo "3. View PostgreSQL logs:"
echo "   docker logs -f $CONTAINER"
echo ""
echo "To restore backups if needed:"
echo "   docker cp ${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP} ${CONTAINER}:/var/lib/postgresql/data/pg_hba.conf"
echo "   docker restart $CONTAINER"
echo ""
