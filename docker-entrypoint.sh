#!/bin/bash
set -e

echo "========================================"
echo "Chatter Docker Container Starting"
echo "========================================"
echo ""

# Function to wait for database
wait_for_db() {
    echo "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; then
            echo "✅ Database is ready!"
            return 0
        fi

        echo "   Attempt $attempt/$max_attempts - Database not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "❌ Database failed to become ready after $max_attempts attempts"
    exit 1
}

# Function to check if migration has been applied
migration_applied() {
    local version=$1
    python3 -c "
import psycopg2
import os
import sys

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    # Check if schema_version table exists
    cur.execute('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'schema_version'
        );
    ''')

    if not cur.fetchone()[0]:
        sys.exit(1)  # Table doesn't exist, migration not applied

    # Check if this version exists
    cur.execute('SELECT COUNT(*) FROM schema_version WHERE version = %s;', ('$version',))
    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    sys.exit(0 if count > 0 else 1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Function to apply migration
apply_migration() {
    local migration_file=$1
    local version=$2
    local description=$3

    echo "📝 Applying migration: $migration_file"

    python3 -c "
import psycopg2
import os
import sys

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    # Read and execute migration file
    with open('$migration_file', 'r') as f:
        migration_sql = f.read()

    cur.execute(migration_sql)

    # Record in schema_version table (if it exists)
    try:
        cur.execute('''
            INSERT INTO schema_version (version, description)
            VALUES (%s, %s)
            ON CONFLICT (version) DO NOTHING;
        ''', ('$version', '$description'))
    except:
        pass  # schema_version table might not exist yet

    conn.commit()
    cur.close()
    conn.close()

    print('✅ Migration applied successfully!')
    sys.exit(0)
except Exception as e:
    print(f'❌ Migration failed: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Main execution
echo "Checking database connection..."
wait_for_db

echo ""
echo "Checking and applying migrations..."
echo "========================================"

# List of migrations in order
declare -a migrations=(
    "migrations/versions/schema_version.sql:schema_version:Create schema version tracking table"
    "migrations/versions/000_create_initial_schema.sql:000:Create initial database schema"
)

# Apply each migration if not already applied
for migration_info in "${migrations[@]}"; do
    IFS=':' read -r file version description <<< "$migration_info"

    if [ ! -f "$file" ]; then
        echo "⚠️  Migration file not found: $file (skipping)"
        continue
    fi

    # Check if already applied
    if migration_applied "$version" 2>/dev/null; then
        echo "✓ Migration $version already applied: $description"
    else
        echo "→ Migration $version not applied yet"
        if apply_migration "$file" "$version" "$description"; then
            echo "✅ Migration $version applied: $description"
        else
            echo "❌ Failed to apply migration $version"
            echo "   Continuing anyway (migration might not be needed)..."
        fi
    fi
done

echo ""
echo "========================================"
echo "✅ All migrations checked/applied"
echo "========================================"
echo ""

echo "Starting application..."
echo "Environment: ${ENVIRONMENT:-development}"
echo "Database: ${DATABASE_URL%%@*}@..."
echo ""

# Execute the main command (passed as arguments)
exec "$@"
