#!/bin/bash
# Diagnose PostgreSQL Docker container issues
# Run on 192.168.2.3

CONTAINER=$(docker ps --filter name=postgres -q | head -1)

if [ -z "$CONTAINER" ]; then
    echo "Error: No PostgreSQL container found"
    echo ""
    echo "Running containers:"
    docker ps
    echo ""
    echo "All containers (including stopped):"
    docker ps -a | grep postgres
    exit 1
fi

echo "========================================="
echo "PostgreSQL Container Diagnostics"
echo "========================================="
echo ""
echo "Container ID: $CONTAINER"
echo ""

echo "=== Container Status ==="
docker ps --filter id=$CONTAINER --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== PostgreSQL Process ==="
docker exec $CONTAINER ps aux 2>&1 | head -20
echo ""

echo "=== PostgreSQL Logs (last 30 lines) ==="
docker logs $CONTAINER --tail 30 2>&1
echo ""

echo "=== Data Directory ==="
docker exec $CONTAINER ls -la /var/lib/postgresql/data/ 2>&1 | head -20
echo ""

echo "=== PostgreSQL Version ==="
docker exec $CONTAINER postgres --version 2>&1
echo ""

echo "=== Check if pg_isready works ==="
docker exec $CONTAINER pg_isready 2>&1
echo ""

echo "=== Network Listening Ports ==="
docker exec $CONTAINER netstat -tlnp 2>/dev/null | grep -i postgres || \
docker exec $CONTAINER ss -tlnp 2>/dev/null | grep -i postgres || \
echo "netstat/ss not available in container"
echo ""

echo "=== Environment Variables ==="
docker exec $CONTAINER env | grep -E "POSTGRES|PG" | sort
echo ""

echo "=== Port Mappings ==="
docker port $CONTAINER
echo ""

echo "=== Container Configuration (PostgreSQL related) ==="
docker inspect $CONTAINER | grep -A 5 -i postgres || echo "No PostgreSQL env vars found"
echo ""

echo "========================================="
echo "Diagnostic Complete"
echo "========================================="
