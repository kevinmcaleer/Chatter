#!/usr/bin/env python3
"""
Apply migration 003: Add force_password_reset column
This script applies the migration directly to the production database
"""

import os
import sys
from dotenv import load_dotenv

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

# Load environment variables - try multiple locations
if os.path.exists('app/.env'):
    print("Loading from app/.env...")
    load_dotenv('app/.env')
elif os.path.exists('.env'):
    print("Loading from .env...")
    load_dotenv('.env')
else:
    print("⚠️  No .env file found, trying environment variables...")

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found")
    print("   Checked locations:")
    print("   - app/.env")
    print("   - .env")
    print("   - Environment variables")
    print()
    print("Please set DATABASE_URL or run from the correct directory")
    sys.exit(1)

def apply_migration():
    """Apply migration 003"""
    print("=" * 50)
    print("Applying Migration 003: force_password_reset")
    print("=" * 50)
    print()

    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("✅ Connected successfully!")
        print()

        # Check if column already exists
        print("Checking if column already exists...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name='user'
                AND column_name='force_password_reset'
            );
        """)

        exists = cur.fetchone()[0]

        if exists:
            print("⚠️  Column 'force_password_reset' already exists!")
            print("   Migration already applied. Nothing to do.")
            cur.close()
            conn.close()
            return True

        print("Column does not exist. Applying migration...")
        print()

        # Read migration file
        with open('migrations/versions/003_add_force_password_reset.sql', 'r') as f:
            migration_sql = f.read()

        # Execute the migration
        print("Executing SQL...")
        cur.execute(migration_sql)

        # Record in schema_version table
        print("Recording migration in schema_version...")
        cur.execute("""
            INSERT INTO schema_version (version, description)
            VALUES (%s, %s)
            ON CONFLICT (version) DO NOTHING;
        """, ('003', 'Add force password reset flag'))

        conn.commit()

        print("✅ Migration applied successfully!")
        print()

        # Verify the change
        print("Verifying changes...")
        cur.execute("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'user'
            AND column_name = 'force_password_reset';
        """)

        result = cur.fetchone()
        if result:
            print(f"✅ Column added: {result[0]} ({result[1]}, default={result[2]}, nullable={result[3]})")

        # Check index
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'user'
            AND indexname = 'idx_user_force_password_reset';
        """)

        index = cur.fetchone()
        if index:
            print(f"✅ Index created: {index[0]}")

        cur.close()
        conn.close()

        print()
        print("=" * 50)
        print("✅ Migration 003 completed successfully!")
        print("=" * 50)
        print()
        print("You can now restart your application:")
        print("  docker-compose restart app")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
