#!/bin/bash
# Check PostgreSQL Docker container configuration
# Run this on 192.168.2.3

echo "========================================="
echo "PostgreSQL Docker Container Check"
echo "========================================="
echo ""

CONTAINER=$(docker ps --filter name=postgres -q | head -1)

if [ -z "$CONTAINER" ]; then
    echo "Error: No PostgreSQL container found"
    exit 1
fi

echo "Container ID: $CONTAINER"
echo ""

echo "Port mappings:"
docker port $CONTAINER
echo ""

echo "Container details:"
docker inspect $CONTAINER | grep -A 10 "PortBindings"
echo ""

echo "PostgreSQL process inside container:"
docker exec $CONTAINER ps aux | grep postgres | head -5
echo ""

echo "PostgreSQL listening ports (inside container):"
docker exec $CONTAINER netstat -tlnp 2>/dev/null | grep postgres || docker exec $CONTAINER ss -tlnp 2>/dev/null | grep postgres || echo "netstat/ss not available"
echo ""

echo "Testing connection on internal port 5432:"
docker exec $CONTAINER psql -U postgres -h localhost -p 5432 -c "SELECT version();" 2>&1 | head -3
echo ""

echo "Testing connection on port 5433:"
docker exec $CONTAINER psql -U postgres -h localhost -p 5433 -c "SELECT version();" 2>&1 | head -3
echo ""
