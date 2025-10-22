#!/usr/bin/env python3
"""
Apply database migrations to PostgreSQL
This script reads migration files and applies them to the production database
"""

import os
import sys
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2 import sql

# Load environment variables
load_dotenv('app/.env')

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in app/.env")
    sys.exit(1)

# Migration files in order
MIGRATIONS = [
    'migrations/versions/000_create_initial_schema.sql',
]

def test_connection():
    """Test database connection"""
    print("Testing database connection...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"   PostgreSQL version: {version.split(',')[0]}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def check_tables():
    """Check what tables exist"""
    print("\nChecking existing tables...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Check for user table
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'user'
            );
        """)
        user_exists = cur.fetchone()[0]

        if user_exists:
            print("✅ Table 'user' exists")

            # Check if it has new fields
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name='user'
                    AND column_name='firstname'
                );
            """)
            has_firstname = cur.fetchone()[0]

            if not has_firstname:
                print("⚠️  Table 'user' missing new fields - migrations needed")
            else:
                print("✅ Table 'user' has new fields")
        else:
            print("⚠️  Table 'user' does not exist")

        # Check for accountlog table
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'accountlog'
            );
        """)
        accountlog_exists = cur.fetchone()[0]

        if accountlog_exists:
            print("✅ Table 'accountlog' exists")
        else:
            print("⚠️  Table 'accountlog' does not exist - migrations needed")

        # Count users
        if user_exists:
            cur.execute('SELECT COUNT(*) FROM "user";')
            count = cur.fetchone()[0]
            print(f"📊 Current user count: {count}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking tables: {e}")

def apply_migration(filepath):
    """Apply a single migration file"""
    print(f"\n📝 Applying {filepath}...")

    try:
        # Read migration file
        with open(filepath, 'r') as f:
            migration_sql = f.read()

        # Connect and execute
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Execute the migration
        cur.execute(migration_sql)
        conn.commit()

        print(f"✅ Migration applied successfully!")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def verify_schema():
    """Verify the final schema"""
    print("\n🔍 Verifying schema...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Get columns in user table
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'user'
            ORDER BY ordinal_position;
        """)

        columns = cur.fetchall()
        print("\nColumns in 'user' table:")
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            print(f"  - {col[0]:<20} {col[1]:<20} {nullable}")

        # Check indexes
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'user'
            ORDER BY indexname;
        """)

        indexes = cur.fetchall()
        print("\nIndexes on 'user' table:")
        for idx in indexes:
            print(f"  - {idx[0]}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error verifying schema: {e}")

def main():
    print("=" * 50)
    print("Database Migration Tool")
    print("=" * 50)
    print()

    # Test connection
    if not test_connection():
        sys.exit(1)

    # Check current state
    check_tables()

    # Ask for confirmation
    print("\n" + "=" * 50)
    response = input("Do you want to apply migrations? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("❌ Migrations cancelled")
        sys.exit(0)

    # Apply each migration
    print("\n" + "=" * 50)
    print("Applying migrations...")
    print("=" * 50)

    for migration_file in MIGRATIONS:
        if not os.path.exists(migration_file):
            print(f"⚠️  Migration file not found: {migration_file}")
            continue

        if not apply_migration(migration_file):
            print(f"\n❌ Stopping - migration failed")
            sys.exit(1)

    # Verify final state
    verify_schema()

    print("\n" + "=" * 50)
    print("✅ All migrations completed successfully!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Start your app: uvicorn app.main:app --port 8001")
    print("2. Create admin user using the API")
    print("3. Update user to admin: UPDATE \"user\" SET type=1 WHERE username='admin';")

if __name__ == '__main__':
    main()
