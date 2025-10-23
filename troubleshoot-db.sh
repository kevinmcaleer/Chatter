#!/bin/bash
# Database Connection Troubleshooting Script
# Run this on your production machine to diagnose connection issues

echo "========================================"
echo "Database Connection Troubleshooting"
echo "========================================"
echo ""

# Load .env file
if [ -f .env ]; then
    echo "✓ Found .env file"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "✗ No .env file found!"
    exit 1
fi

echo ""
echo "1. Checking Environment Variables"
echo "-----------------------------------"
echo "DATABASE_URL: ${DATABASE_URL:0:20}..." # Show first 20 chars only
echo "DB_HOST: ${DB_HOST}"
echo "DB_PORT: ${DB_PORT}"
echo "DB_NAME: ${DB_NAME}"
echo "DB_USER: ${DB_USER:0:5}..." # Show first 5 chars only
echo ""

echo "2. Testing Network Connectivity"
echo "-----------------------------------"

# Extract host and port from DATABASE_URL if needed
if [ -n "$DATABASE_URL" ]; then
    # Parse DATABASE_URL to get host and port
    DB_HOST_FROM_URL=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT_FROM_URL=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    if [ -n "$DB_HOST_FROM_URL" ]; then
        echo "Using DATABASE_URL: $DB_HOST_FROM_URL:$DB_PORT_FROM_URL"
        TEST_HOST=$DB_HOST_FROM_URL
        TEST_PORT=$DB_PORT_FROM_URL
    fi
else
    TEST_HOST=${DB_HOST}
    TEST_PORT=${DB_PORT}
fi

echo ""
echo "Testing connection to: $TEST_HOST:$TEST_PORT"
echo ""

# Test ping
echo -n "Ping test: "
if ping -c 1 -W 2 $TEST_HOST > /dev/null 2>&1; then
    echo "✓ Host is reachable"
else
    echo "✗ Host is NOT reachable (this might be normal if ICMP is blocked)"
fi

# Test port
echo -n "Port test: "
if command -v nc > /dev/null; then
    if nc -zv -w 2 $TEST_HOST $TEST_PORT 2>&1 | grep -q succeeded; then
        echo "✓ Port $TEST_PORT is open"
    else
        echo "✗ Port $TEST_PORT is NOT accessible"
        echo "  This is the likely problem!"
    fi
elif command -v telnet > /dev/null; then
    if timeout 2 telnet $TEST_HOST $TEST_PORT 2>&1 | grep -q Connected; then
        echo "✓ Port $TEST_PORT is open"
    else
        echo "✗ Port $TEST_PORT is NOT accessible"
    fi
else
    echo "⚠ nc or telnet not available, cannot test port"
fi

echo ""
echo "3. Docker Network Check"
echo "-----------------------------------"
echo "Docker networks:"
docker network ls

echo ""
echo "Container network settings:"
docker inspect chatter-app 2>/dev/null | grep -A 10 "Networks" || echo "Container not running"

echo ""
echo "4. PostgreSQL Connection Test"
echo "-----------------------------------"
echo "Attempting direct connection from host..."

if [ -n "$DATABASE_URL" ]; then
    docker run --rm postgres:16-alpine psql "$DATABASE_URL" -c "SELECT version();" 2>&1 | head -5
else
    echo "DATABASE_URL not set, skipping direct test"
fi

echo ""
echo "========================================"
echo "Troubleshooting Complete"
echo "========================================"
echo ""
echo "Common Issues:"
echo "1. Firewall blocking port $TEST_PORT"
echo "2. PostgreSQL not configured to accept remote connections"
echo "3. PostgreSQL pg_hba.conf not allowing connections from Docker IP"
echo "4. Wrong host/port in DATABASE_URL"
echo "5. Network routing issue between Docker and database server"
echo ""
echo "Next Steps:"
echo "1. If port test failed: Check firewall rules on $TEST_HOST"
echo "2. If port is open but connection fails: Check PostgreSQL logs"
echo "3. Verify PostgreSQL pg_hba.conf allows connections from this IP"
echo "4. Check if DATABASE_URL credentials are URL-encoded properly"
