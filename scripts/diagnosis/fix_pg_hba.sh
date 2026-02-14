#!/bin/bash
# Quick fix script for PostgreSQL pg_hba.conf
# Run this on the database server (192.168.2.3) as a user with sudo privileges

set -e

echo "========================================="
echo "PostgreSQL Access Configuration Fix"
echo "========================================="
echo ""

# Find PostgreSQL version
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
echo "Detected PostgreSQL version: $PG_VERSION"

# Configuration paths
PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"
PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"

# Backup files
BACKUP_DIR="/var/backups/postgresql"
sudo mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo ""
echo "Step 1: Backing up configuration files..."
sudo cp "$PG_HBA" "${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP}"
sudo cp "$PG_CONF" "${BACKUP_DIR}/postgresql.conf.backup.${TIMESTAMP}"
echo "✓ Backups created in $BACKUP_DIR"

echo ""
echo "Step 2: Checking if user 'kev' exists..."
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='kev'" | grep -q 1; then
    echo "✓ User 'kev' exists"
else
    echo "Creating user 'kev'..."
    sudo -u postgres psql << EOF
CREATE USER kev WITH PASSWORD 'monkeybaby';
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO kev;
EOF
    echo "✓ User 'kev' created"
fi

echo ""
echo "Step 3: Ensuring user 'kev' has correct password..."
sudo -u postgres psql -c "ALTER USER kev WITH PASSWORD 'monkeybaby';" > /dev/null
echo "✓ Password set"

echo ""
echo "Step 4: Granting database permissions..."
sudo -u postgres psql kevsrobots_cms << 'EOF'
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO kev;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kev;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO kev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO kev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO kev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO kev;
EOF
echo "✓ Permissions granted"

echo ""
echo "Step 5: Updating pg_hba.conf..."

# Create new pg_hba.conf content
sudo tee "${PG_HBA}.new" > /dev/null << 'EOF'
# PostgreSQL Client Authentication Configuration File
# ===================================================
# This file controls: which hosts are allowed to connect, how clients
# are authenticated, which PostgreSQL user names they can use, which
# databases they can access.

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections:
host    all             postgres        127.0.0.1/32            scram-sha-256

# ===================================================
# CHATTER APPLICATION ACCESS
# Allow Chatter servers to connect to kevsrobots_cms database
# ===================================================
host    kevsrobots_cms  kev             192.168.2.1/32          md5
host    kevsrobots_cms  kev             192.168.2.2/32          md5
host    kevsrobots_cms  kev             192.168.2.3/32          md5
host    kevsrobots_cms  kev             192.168.2.4/32          md5

# Alternative: Allow entire 192.168.2.0/24 subnet (uncomment to use)
# host    kevsrobots_cms  kev             192.168.2.0/24          md5

# IPv4 local connections (other users)
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256

# Reject all other connection attempts
# host    all             all             0.0.0.0/0               reject
EOF

# Replace pg_hba.conf
sudo mv "${PG_HBA}.new" "$PG_HBA"
sudo chown postgres:postgres "$PG_HBA"
sudo chmod 640 "$PG_HBA"
echo "✓ pg_hba.conf updated"

echo ""
echo "Step 6: Checking postgresql.conf listen_addresses..."
if sudo grep -q "^listen_addresses.*=.*'\\*'" "$PG_CONF"; then
    echo "✓ listen_addresses already set to '*'"
elif sudo grep -q "^listen_addresses" "$PG_CONF"; then
    echo "Updating listen_addresses..."
    sudo sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
    echo "✓ listen_addresses updated"
else
    echo "Adding listen_addresses setting..."
    sudo sed -i "/^#listen_addresses/a listen_addresses = '*'" "$PG_CONF"
    echo "✓ listen_addresses added"
fi

echo ""
echo "Step 7: Reloading PostgreSQL configuration..."
sudo systemctl reload postgresql
echo "✓ PostgreSQL reloaded"

echo ""
echo "Step 8: Testing configuration..."
sleep 2

# Test local connection
echo -n "Testing local connection... "
if PGPASSWORD='monkeybaby' psql -h localhost -p 5433 -U kev -d kevsrobots_cms -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
fi

# Test network connection
echo -n "Testing network connection (192.168.2.3)... "
if PGPASSWORD='monkeybaby' psql -h 192.168.2.3 -p 5433 -U kev -d kevsrobots_cms -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
fi

echo ""
echo "========================================="
echo "Configuration complete!"
echo "========================================="
echo ""
echo "Backups saved to: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Test connection from Chatter server (192.168.2.2):"
echo "   PGPASSWORD='monkeybaby' psql -h 192.168.2.3 -p 5433 -U kev -d kevsrobots_cms -c 'SELECT version();'"
echo ""
echo "2. If issues persist, check logs:"
echo "   sudo tail -f /var/log/postgresql/postgresql-${PG_VERSION}-main.log"
echo ""
echo "3. To restore backups if needed:"
echo "   sudo cp ${BACKUP_DIR}/pg_hba.conf.backup.${TIMESTAMP} $PG_HBA"
echo "   sudo systemctl reload postgresql"
echo ""
