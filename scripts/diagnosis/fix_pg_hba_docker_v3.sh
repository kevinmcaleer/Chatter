#!/bin/bash
# Fix PostgreSQL pg_hba.conf on Docker-based database server
# Run this ON the database server (192.168.2.3)

set -e

echo "========================================="
echo "PostgreSQL Docker Configuration Fix v3"
echo "Database Server: 192.168.2.3"
echo "========================================="
echo ""

# PostgreSQL credentials
PG_USERNAME="Hd4AZn:NlSpH"
PG_PASSWORD="8&0+6849Mx#S"
PG_DATABASE="kevsrobots_cms"
PG_PORT_EXTERNAL="5433"  # External port (host machine)
PG_PORT_INTERNAL="5432"  # Internal port (inside container)

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

echo "Detecting internal PostgreSQL port..."
if docker exec $CONTAINER psql -U postgres -h localhost -p 5432 -c "SELECT 1;" > /dev/null 2>&1; then
    PG_PORT_INTERNAL="5432"
    echo "✓ PostgreSQL running on internal port 5432"
elif docker exec $CONTAINER psql -U postgres -h localhost -p 5433 -c "SELECT 1;" > /dev/null 2>&1; then
    PG_PORT_INTERNAL="5433"
    echo "✓ PostgreSQL running on internal port 5433"
else
    echo "✗ Cannot connect to PostgreSQL on ports 5432 or 5433"
    echo "Trying without specifying port..."
    if docker exec $CONTAINER psql -U postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✓ PostgreSQL accessible via Unix socket"
        USE_UNIX_SOCKET=true
    else
        echo "✗ Cannot connect to PostgreSQL at all"
        exit 1
    fi
fi
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

# Build psql command based on connection method
if [ "$USE_UNIX_SOCKET" = true ]; then
    PSQL_CMD="docker exec $CONTAINER psql -U postgres"
else
    PSQL_CMD="docker exec $CONTAINER psql -U postgres -h localhost -p $PG_PORT_INTERNAL"
fi

# Check if user exists
USER_EXISTS=$($PSQL_CMD -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USERNAME'" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" = "1" ]; then
    echo "✓ User '$PG_USERNAME' exists"
else
    echo "Creating user '$PG_USERNAME'..."
    $PSQL_CMD -c "CREATE USER \"$PG_USERNAME\" WITH PASSWORD '$PG_PASSWORD';"
    echo "✓ User '$PG_USERNAME' created"
fi

echo ""
echo "==================================================================="
echo "Step 3: Setting user password..."
echo "==================================================================="
$PSQL_CMD -c "ALTER USER \"$PG_USERNAME\" WITH PASSWORD '$PG_PASSWORD';" > /dev/null
echo "✓ Password set for user '$PG_USERNAME'"

echo ""
echo "==================================================================="
echo "Step 4: Granting database permissions..."
echo "==================================================================="

# Grant database-level permissions
echo "Granting database privileges..."
$PSQL_CMD -c "GRANT ALL PRIVILEGES ON DATABASE $PG_DATABASE TO \"$PG_USERNAME\";" > /dev/null

# Grant schema-level permissions
echo "Granting schema privileges..."
$PSQL_CMD -d $PG_DATABASE -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$PG_USERNAME\";" > /dev/null
$PSQL_CMD -d $PG_DATABASE -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"$PG_USERNAME\";" > /dev/null
$PSQL_CMD -d $PG_DATABASE -c "GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO \"$PG_USERNAME\";" > /dev/null
$PSQL_CMD -d $PG_DATABASE -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO \"$PG_USERNAME\";" > /dev/null
$PSQL_CMD -d $PG_DATABASE -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO \"$PG_USERNAME\";" > /dev/null
$PSQL_CMD -d $PG_DATABASE -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO \"$PG_USERNAME\";" > /dev/null
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

# Allow entire 192.168.2.0/24 subnet (for easier management)
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.0/24          md5

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
echo "Step 7: Restarting PostgreSQL container to apply changes..."
echo "==================================================================="

docker restart $CONTAINER
echo "Waiting for PostgreSQL to start..."
sleep 5

# Wait for PostgreSQL to be ready
for i in {1..10}; do
    if docker exec $CONTAINER pg_isready > /dev/null 2>&1; then
        echo "✓ PostgreSQL is ready"
        break
    fi
    echo "Waiting... ($i/10)"
    sleep 2
done

echo ""
echo "==================================================================="
echo "Step 8: Testing configuration..."
echo "==================================================================="

# Test connection from inside container (using internal port)
echo -n "Testing connection from inside container... "
if [ "$USE_UNIX_SOCKET" = true ]; then
    TEST_CMD="docker exec -e PGPASSWORD='$PG_PASSWORD' $CONTAINER psql -U '$PG_USERNAME' -d $PG_DATABASE -c 'SELECT 1;'"
else
    TEST_CMD="docker exec -e PGPASSWORD='$PG_PASSWORD' $CONTAINER psql -h localhost -p $PG_PORT_INTERNAL -U '$PG_USERNAME' -d $PG_DATABASE -c 'SELECT 1;'"
fi

if eval "$TEST_CMD" > /dev/null 2>&1; then
    echo "✓ SUCCESS"
    INTERNAL_TEST=true
else
    echo "✗ FAILED"
    INTERNAL_TEST=false
fi

# Test connection from host (if psql is installed) using external port
if command -v psql &> /dev/null; then
    echo -n "Testing connection from host (192.168.2.3:$PG_PORT_EXTERNAL)... "
    if PGPASSWORD="$PG_PASSWORD" psql -h 192.168.2.3 -p $PG_PORT_EXTERNAL -U "$PG_USERNAME" -d "$PG_DATABASE" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✓ SUCCESS"
        EXTERNAL_TEST=true
    else
        echo "✗ FAILED"
        EXTERNAL_TEST=false
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
echo "  Port (external): $PG_PORT_EXTERNAL"
echo "  Port (internal): $PG_PORT_INTERNAL"
echo "  Database: $PG_DATABASE"
echo "  Username: $PG_USERNAME"
echo "  Container: $CONTAINER"
echo ""
echo "Test results:"
if [ "$INTERNAL_TEST" = true ]; then
    echo "  ✓ Internal connection: WORKING"
else
    echo "  ✗ Internal connection: FAILED"
fi
if [ "$EXTERNAL_TEST" = true ]; then
    echo "  ✓ External connection: WORKING"
elif [ "$EXTERNAL_TEST" = false ]; then
    echo "  ✗ External connection: FAILED"
else
    echo "  ⚠ External connection: NOT TESTED"
fi
echo ""
echo "Allowed client IPs: 192.168.2.0/24 (entire subnet)"
echo ""
echo "Backups saved to: $BACKUP_DIR"
echo ""

if [ "$EXTERNAL_TEST" = true ] || [ "$INTERNAL_TEST" = true ]; then
    echo "✓ Configuration successful!"
    echo ""
    echo "Next step: Test from Chatter server or your local machine"
else
    echo "⚠ Configuration may need troubleshooting"
    echo ""
    echo "View PostgreSQL logs:"
    echo "   docker logs -f $CONTAINER"
    echo ""
    echo "To restore backups:"
    echo "   docker cp ${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP} ${CONTAINER}:/var/lib/postgresql/data/pg_hba.conf"
    echo "   docker restart $CONTAINER"
fi
echo ""
