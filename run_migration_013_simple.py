#!/usr/bin/env python3
"""
Simple migration runner for Migration 013.
Reads DATABASE_URL from .env file and executes the migration.
"""
import os
import sys

# Check if psycopg2 is available
try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2-binary not installed")
    print("Install with: pip install psycopg2-binary")
    sys.exit(1)

# Check if python-dotenv is available
try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed")
    print("Install with: pip install python-dotenv")
    sys.exit(1)

# Load environment variables from .env
load_dotenv()

# Get DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

print(f"Database: {DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'unknown'}")

# Migration SQL
migration_sql = """
-- Migration 013: Add user profile fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS profile_picture VARCHAR;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS location VARCHAR;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS bio TEXT;

INSERT INTO schema_version (version, description, applied_at)
VALUES (13, 'Add user profile fields (profile_picture, location, bio)', NOW())
ON CONFLICT DO NOTHING;
"""

try:
    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Check if migration already applied
    print("📋 Checking current schema version...")
    cursor.execute("SELECT COUNT(*) FROM schema_version WHERE version = '13';")
    already_applied = cursor.fetchone()[0] > 0

    if already_applied:
        print("⚠️  Migration 013 is already applied!")
        response = input("Run it again anyway? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Aborted")
            sys.exit(0)

    # Execute migration
    print("\n🚀 Executing Migration 013...")
    cursor.execute(migration_sql)
    conn.commit()
    print("✅ Migration SQL executed successfully!")

    # Verify schema version
    print("\n📊 Verifying schema version...")
    cursor.execute("SELECT version, description, applied_at FROM schema_version WHERE version = '13';")
    result = cursor.fetchone()
    if result:
        print(f"  Version {result[0]}: {result[1]}")
        print(f"  Applied at: {result[2]}")
    else:
        print("  ⚠️  Warning: Schema version 13 not found in table")

    # Verify new columns
    print("\n🔍 Verifying new columns...")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'user'
        AND column_name IN ('profile_picture', 'location', 'bio')
        ORDER BY column_name;
    """)
    columns = cursor.fetchall()

    if columns:
        print("  ✅ Columns added to 'user' table:")
        for col_name, data_type in columns:
            print(f"     - {col_name} ({data_type})")
    else:
        print("  ⚠️  Warning: New columns not found")

    # Close connection
    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ MIGRATION 013 COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set environment variables for NAS:")
    print("   export NAS_HOST=192.168.1.79")
    print("   export NAS_USERNAME=kevsrobots")
    print("   export NAS_PASSWORD=<your-password>")
    print("   export NAS_SHARE_NAME=chatter")
    print("2. Deploy updated Chatter app with new dependencies")
    print("3. Test profile endpoints:")
    print("   curl https://chatter.kevsrobots.com/profile/<username>")

except psycopg2.Error as e:
    print(f"\n❌ Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
