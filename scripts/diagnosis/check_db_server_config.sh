#!/bin/bash
# Diagnostic script for PostgreSQL server at 192.168.2.3
# Run this script ON the database server to check configuration

echo "==================================================================="
echo "PostgreSQL Database Server Configuration Check"
echo "==================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if PostgreSQL is running
echo "1. Checking PostgreSQL service status..."
if systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL is NOT running${NC}"
    echo "  Run: sudo systemctl start postgresql"
fi
echo ""

# 2. Check which port PostgreSQL is listening on
echo "2. Checking PostgreSQL listening ports..."
netstat -tlnp 2>/dev/null | grep postgres || ss -tlnp 2>/dev/null | grep postgres
echo ""

# 3. Check pg_hba.conf location and contents
echo "3. Checking pg_hba.conf configuration..."
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
PG_HBA_PATH="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"

if [ -f "$PG_HBA_PATH" ]; then
    echo "Found pg_hba.conf at: $PG_HBA_PATH"
    echo ""
    echo "Current non-comment lines:"
    echo "-------------------------------------------------------------------"
    grep -v '^#' "$PG_HBA_PATH" | grep -v '^$'
    echo "-------------------------------------------------------------------"
else
    echo -e "${YELLOW}Warning: Could not find pg_hba.conf at expected location${NC}"
    echo "Searching for pg_hba.conf..."
    find /etc/postgresql -name pg_hba.conf 2>/dev/null
fi
echo ""

# 4. Check postgresql.conf for listen_addresses
echo "4. Checking postgresql.conf for listen_addresses..."
PG_CONF_PATH="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"
if [ -f "$PG_CONF_PATH" ]; then
    echo "Found postgresql.conf at: $PG_CONF_PATH"
    echo "Current listen_addresses setting:"
    grep "^listen_addresses" "$PG_CONF_PATH" || echo "  (commented out - using default 'localhost')"
    echo ""
    echo "Current port setting:"
    grep "^port" "$PG_CONF_PATH" || echo "  (commented out - using default 5432)"
fi
echo ""

# 5. Check if user 'kev' exists in PostgreSQL
echo "5. Checking if user 'kev' exists..."
sudo -u postgres psql -c "\du kev" 2>&1
echo ""

# 6. Check if database 'kevsrobots_cms' exists
echo "6. Checking if database 'kevsrobots_cms' exists..."
sudo -u postgres psql -c "\l kevsrobots_cms" 2>&1
echo ""

# 7. Test local connection
echo "7. Testing local connection as user 'kev'..."
psql -h localhost -p 5433 -U kev -d kevsrobots_cms -c "SELECT version();" 2>&1
echo ""

echo "==================================================================="
echo "Recommended pg_hba.conf configuration for your setup:"
echo "==================================================================="
echo ""
echo "# TYPE  DATABASE        USER            ADDRESS                 METHOD"
echo "# Allow connections from Chatter servers (192.168.2.1, 192.168.2.2)"
echo "host    kevsrobots_cms  kev             192.168.2.1/32          md5"
echo "host    kevsrobots_cms  kev             192.168.2.2/32          md5"
echo "host    kevsrobots_cms  kev             192.168.2.3/32          md5"
echo "host    kevsrobots_cms  kev             192.168.2.4/32          md5"
echo ""
echo "# Or allow entire subnet (less secure but simpler)"
echo "host    kevsrobots_cms  kev             192.168.2.0/24          md5"
echo ""
echo "NOTE: After modifying pg_hba.conf, reload PostgreSQL:"
echo "  sudo systemctl reload postgresql"
echo ""
echo "==================================================================="
