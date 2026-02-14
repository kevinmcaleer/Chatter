#!/bin/bash
# Fix PostgreSQL pg_hba.conf on rebuilt database server (192.168.2.3)
# Run this ON the database server as a user with sudo privileges

set -e

echo "========================================="
echo "PostgreSQL Access Configuration Fix"
echo "Rebuilt Server: 192.168.2.3"
echo "========================================="
echo ""

# PostgreSQL username from .env
PG_USERNAME="Hd4AZn:NlSpH"
PG_PASSWORD="8&0+6849Mx#S"
PG_DATABASE="kevsrobots_cms"

# Find PostgreSQL version
if command -v psql &> /dev/null; then
    PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
elif command -v docker &> /dev/null && docker ps | grep -q postgres; then
    echo "Detected PostgreSQL running in Docker container"
    PG_VERSION=$(docker exec $(docker ps --filter name=postgres -q | head -1) psql --version | grep -oP '\d+' | head -1)
    DOCKER_MODE=true
else
    echo "Error: Cannot find PostgreSQL installation"
    exit 1
fi

echo "Detected PostgreSQL version: $PG_VERSION"
echo "Docker mode: ${DOCKER_MODE:-false}"
echo ""

# Configuration paths (adjust based on Docker/native installation)
if [ "$DOCKER_MODE" = "true" ]; then
    CONTAINER_NAME=$(docker ps --filter name=postgres -q | head -1)
    echo "PostgreSQL container: $CONTAINER_NAME"
    PG_HBA="/var/lib/postgresql/data/pg_hba.conf"
    PG_CONF="/var/lib/postgresql/data/postgresql.conf"
else
    PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"
    PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"
fi

# Backup directory
BACKUP_DIR="/var/backups/postgresql"
sudo mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "==================================================================="
echo "Step 1: Backing up configuration files..."
echo "==================================================================="

if [ "$DOCKER_MODE" = "true" ]; then
    docker cp "${CONTAINER_NAME}:${PG_HBA}" "${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP}"
    docker cp "${CONTAINER_NAME}:${PG_CONF}" "${BACKUP_DIR}/postgresql.conf.backup.${TIMESTAMP}"
else
    sudo cp "$PG_HBA" "${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP}"
    sudo cp "$PG_CONF" "${BACKUP_DIR}/postgresql.conf.backup.${TIMESTAMP}"
fi
echo "✓ Backups created in $BACKUP_DIR"

echo ""
echo "==================================================================="
echo "Step 2: Checking if PostgreSQL user exists..."
echo "==================================================================="

# Need to escape special characters for shell
PG_USERNAME_ESCAPED=$(printf '%s\n' "$PG_USERNAME" | sed 's/[]\/$*.^[]/\\&/g')

if [ "$DOCKER_MODE" = "true" ]; then
    USER_EXISTS=$(docker exec -e PGPASSWORD='' $CONTAINER_NAME psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USERNAME'" || echo "0")
else
    USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USERNAME'" || echo "0")
fi

if [ "$USER_EXISTS" = "1" ]; then
    echo "✓ User '$PG_USERNAME' exists"
else
    echo "Creating user '$PG_USERNAME'..."
    if [ "$DOCKER_MODE" = "true" ]; then
        docker exec $CONTAINER_NAME psql -U postgres << EOF
CREATE USER "$PG_USERNAME" WITH PASSWORD '$PG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $PG_DATABASE TO "$PG_USERNAME";
EOF
    else
        sudo -u postgres psql << EOF
CREATE USER "$PG_USERNAME" WITH PASSWORD '$PG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $PG_DATABASE TO "$PG_USERNAME";
EOF
    fi
    echo "✓ User '$PG_USERNAME' created"
fi

echo ""
echo "==================================================================="
echo "Step 3: Ensuring user has correct password..."
echo "==================================================================="

if [ "$DOCKER_MODE" = "true" ]; then
    docker exec $CONTAINER_NAME psql -U postgres -c "ALTER USER \"$PG_USERNAME\" WITH PASSWORD '$PG_PASSWORD';" > /dev/null
else
    sudo -u postgres psql -c "ALTER USER \"$PG_USERNAME\" WITH PASSWORD '$PG_PASSWORD';" > /dev/null
fi
echo "✓ Password set for user '$PG_USERNAME'"

echo ""
echo "==================================================================="
echo "Step 4: Granting database permissions..."
echo "==================================================================="

if [ "$DOCKER_MODE" = "true" ]; then
    docker exec $CONTAINER_NAME psql -U postgres $PG_DATABASE << EOF
GRANT ALL PRIVILEGES ON DATABASE $PG_DATABASE TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO "$PG_USERNAME";
EOF
else
    sudo -u postgres psql $PG_DATABASE << EOF
GRANT ALL PRIVILEGES ON DATABASE $PG_DATABASE TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$PG_USERNAME";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "$PG_USERNAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO "$PG_USERNAME";
EOF
fi
echo "✓ Permissions granted to user '$PG_USERNAME'"

echo ""
echo "==================================================================="
echo "Step 5: Updating pg_hba.conf..."
echo "==================================================================="

# Create new pg_hba.conf content
cat > /tmp/pg_hba.conf.new << 'EOF'
# PostgreSQL Client Authentication Configuration File
# ===================================================
# Database recovered from backup on 2026-02-14 after disk failure
# Configuration for Chatter application

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections:
host    all             postgres        127.0.0.1/32            scram-sha-256

# ===================================================
# CHATTER APPLICATION ACCESS
# Username: Hd4AZn:NlSpH (note: contains special characters)
# Allow Chatter servers to connect to kevsrobots_cms database
# ===================================================
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.1/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.2/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.3/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.4/32          md5

# Alternative: Allow entire 192.168.2.0/24 subnet (uncomment to use)
# host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.0/24          md5

# IPv4 local connections (other users)
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
EOF

# Deploy pg_hba.conf
if [ "$DOCKER_MODE" = "true" ]; then
    docker cp /tmp/pg_hba.conf.new "${CONTAINER_NAME}:${PG_HBA}"
    docker exec $CONTAINER_NAME chown postgres:postgres "$PG_HBA"
    docker exec $CONTAINER_NAME chmod 640 "$PG_HBA"
else
    sudo mv /tmp/pg_hba.conf.new "$PG_HBA"
    sudo chown postgres:postgres "$PG_HBA"
    sudo chmod 640 "$PG_HBA"
fi
echo "✓ pg_hba.conf updated"

echo ""
echo "==================================================================="
echo "Step 6: Checking postgresql.conf listen_addresses..."
echo "==================================================================="

check_listen_addresses() {
    if [ "$DOCKER_MODE" = "true" ]; then
        docker exec $CONTAINER_NAME grep "^listen_addresses" "$PG_CONF" || echo ""
    else
        sudo grep "^listen_addresses" "$PG_CONF" || echo ""
    fi
}

CURRENT_LISTEN=$(check_listen_addresses)

if echo "$CURRENT_LISTEN" | grep -q "listen_addresses.*=.*'\\*'"; then
    echo "✓ listen_addresses already set to '*'"
else
    echo "Setting listen_addresses to '*'..."
    if [ "$DOCKER_MODE" = "true" ]; then
        # For Docker, we need to edit the file differently
        docker exec $CONTAINER_NAME sh -c "echo \"listen_addresses = '*'\" >> $PG_CONF.custom"
        docker exec $CONTAINER_NAME sh -c "grep -v '^listen_addresses' $PG_CONF > $PG_CONF.tmp && cat $PG_CONF.custom >> $PG_CONF.tmp && mv $PG_CONF.tmp $PG_CONF"
        docker exec $CONTAINER_NAME rm -f $PG_CONF.custom
    else
        if sudo grep -q "^listen_addresses" "$PG_CONF"; then
            sudo sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
        else
            sudo sed -i "/^#listen_addresses/a listen_addresses = '*'" "$PG_CONF"
        fi
    fi
    echo "✓ listen_addresses updated"
fi

echo ""
echo "==================================================================="
echo "Step 7: Reloading PostgreSQL configuration..."
echo "==================================================================="

if [ "$DOCKER_MODE" = "true" ]; then
    echo "Restarting PostgreSQL container..."
    docker restart $CONTAINER_NAME
    echo "Waiting for PostgreSQL to start..."
    sleep 5
else
    sudo systemctl reload postgresql
fi
echo "✓ PostgreSQL configuration reloaded"

echo ""
echo "==================================================================="
echo "Step 8: Testing configuration..."
echo "==================================================================="

sleep 3

# Test local connection
echo -n "Testing local connection... "
if PGPASSWORD="$PG_PASSWORD" psql -h localhost -p 5433 -U "$PG_USERNAME" -d "$PG_DATABASE" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
    echo "Note: This may be normal if psql client is not installed locally"
fi

# Test network connection
echo -n "Testing network connection (192.168.2.3)... "
if PGPASSWORD="$PG_PASSWORD" psql -h 192.168.2.3 -p 5433 -U "$PG_USERNAME" -d "$PG_DATABASE" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
    echo "Note: This may be normal if psql client is not installed locally"
fi

echo ""
echo "==================================================================="
echo "Configuration Complete!"
echo "==================================================================="
echo ""
echo "Database server details:"
echo "  Host: 192.168.2.3"
echo "  Port: 5433"
echo "  Database: $PG_DATABASE"
echo "  Username: $PG_USERNAME"
echo "  Allowed clients: 192.168.2.1, 192.168.2.2, 192.168.2.3, 192.168.2.4"
echo ""
echo "Backups saved to: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Test connection from a Chatter server (192.168.2.2):"
echo "   PGPASSWORD='$PG_PASSWORD' psql -h 192.168.2.3 -p 5433 -U '$PG_USERNAME' -d $PG_DATABASE -c 'SELECT version();'"
echo ""
echo "2. Restart Chatter applications on servers to reconnect"
echo ""
echo "3. Monitor PostgreSQL logs for connection attempts:"
if [ "$DOCKER_MODE" = "true" ]; then
    echo "   docker logs -f $CONTAINER_NAME"
else
    echo "   sudo tail -f /var/log/postgresql/postgresql-${PG_VERSION}-main.log"
fi
echo ""
echo "To restore backups if needed:"
if [ "$DOCKER_MODE" = "true" ]; then
    echo "   docker cp ${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP} ${CONTAINER_NAME}:${PG_HBA}"
    echo "   docker restart $CONTAINER_NAME"
else
    echo "   sudo cp ${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP} $PG_HBA"
    echo "   sudo systemctl reload postgresql"
fi
echo ""
