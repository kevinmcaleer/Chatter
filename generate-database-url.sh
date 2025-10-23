#!/bin/bash
# Helper script to generate DATABASE_URL from .env variables
# This is useful when running with 'docker run' instead of 'docker-compose'

set -e

if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Load environment variables from .env
export $(cat .env | grep -v '^#' | xargs)

if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ]; then
    echo "Error: Missing required database variables in .env file"
    echo "Required: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME"
    exit 1
fi

# Construct DATABASE_URL
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "========================================="
echo "Generated DATABASE_URL"
echo "========================================="
echo ""
echo "Add this line to your .env file:"
echo ""
echo "DATABASE_URL=\"${DATABASE_URL}\""
echo ""
echo "========================================="
echo ""
echo "IMPORTANT: Verify that DB_USER and DB_PASSWORD"
echo "in your .env file are already URL-encoded!"
echo ""
echo "If they contain special characters like : @ # & +"
echo "they must be encoded (see FIX_ENV_FILE.md)"
echo ""

# Test if it works
echo "Testing connection with this DATABASE_URL..."
echo ""

docker run --rm postgres:16-alpine psql "$DATABASE_URL" -c "SELECT 1 AS test;" 2>&1 | head -10

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Connection successful!"
    echo ""
    echo "You can now add DATABASE_URL to your .env file"
else
    echo ""
    echo "❌ Connection failed!"
    echo ""
    echo "Check:"
    echo "1. DB_USER and DB_PASSWORD are URL-encoded in .env"
    echo "2. PostgreSQL is running on $DB_HOST:$DB_PORT"
    echo "3. Firewall allows connections"
    echo "4. pg_hba.conf allows connections from this host"
fi
