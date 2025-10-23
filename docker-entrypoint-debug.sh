#!/bin/bash
set -e

echo "========================================"
echo "Chatter Docker Container Starting (DEBUG MODE)"
echo "========================================"
echo ""

echo "Environment Check:"
echo "-----------------------------------"
echo "DATABASE_URL: ${DATABASE_URL:0:30}..." # First 30 chars
echo "PORT: ${PORT:-8000}"
echo "ENVIRONMENT: ${ENVIRONMENT:-development}"
echo ""

# Function to wait for database with better error messages
wait_for_db() {
    echo "Checking database connection..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "   Attempt $attempt/$max_attempts..."

        # Run connection test and capture error
        ERROR_OUTPUT=$(python3 -c "
import psycopg2
import os
import sys
try:
    print('Attempting to connect to:', os.getenv('DATABASE_URL')[:50] + '...', file=sys.stderr)
    conn = psycopg2.connect(os.getenv('DATABASE_URL'), connect_timeout=5)
    conn.close()
    print('✅ Connection successful!', file=sys.stderr)
    sys.exit(0)
except psycopg2.OperationalError as e:
    print(f'❌ OperationalError: {e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)

        EXIT_CODE=$?
        echo "$ERROR_OUTPUT"

        if [ $EXIT_CODE -eq 0 ]; then
            echo "✅ Database is ready!"
            return 0
        fi

        if [ $attempt -ge 3 ]; then
            echo ""
            echo "⚠️  Still failing after $attempt attempts. Common issues:"
            echo "   1. Check DATABASE_URL is set correctly"
            echo "   2. Verify PostgreSQL server is running on the target host"
            echo "   3. Check firewall allows connections to PostgreSQL port"
            echo "   4. Verify PostgreSQL pg_hba.conf allows remote connections"
            echo "   5. Check if credentials are URL-encoded (: = %3A, @ = %40, etc.)"
            echo ""
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    echo "❌ Database failed to become ready after $max_attempts attempts"
    echo ""
    echo "Final troubleshooting steps:"
    echo "1. From the Docker host, try: nc -zv <db_host> <db_port>"
    echo "2. Check PostgreSQL logs on the database server"
    echo "3. Verify the container can resolve the database hostname"
    echo "4. Check if DATABASE_URL format is: postgresql://user:pass@host:port/dbname"
    exit 1
}

# Main execution
echo "Checking database connection..."
wait_for_db

echo ""
echo "Database connection successful! Proceeding with migrations..."
echo ""

# Execute the original entrypoint for migrations
exec /app/docker-entrypoint.sh "$@"
