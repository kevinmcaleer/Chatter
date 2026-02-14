#!/usr/bin/env python3
"""
Run migration 013 to add user profile fields.
This script reads the migration SQL file and executes it against the database.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

# Read migration file
migration_file = Path(__file__).parent / "migrations" / "versions" / "013_add_user_profile_fields.sql"

if not migration_file.exists():
    print(f"ERROR: Migration file not found: {migration_file}")
    sys.exit(1)

print(f"Reading migration from: {migration_file}")
migration_sql = migration_file.read_text()

print("\nMigration SQL:")
print("=" * 60)
print(migration_sql)
print("=" * 60)

# Connect to database
print(f"\nConnecting to database...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Check current schema version
    print("\nChecking current schema version...")
    cursor.execute("SELECT version, description, applied_at FROM schema_version ORDER BY version DESC LIMIT 5;")
    current_versions = cursor.fetchall()

    print("\nCurrent schema versions:")
    for version, description, applied_at in current_versions:
        print(f"  Version {version}: {description} (applied {applied_at})")

    # Check if migration 013 already applied
    cursor.execute("SELECT COUNT(*) FROM schema_version WHERE version = 13;")
    count = cursor.fetchone()[0]

    if count > 0:
        print("\n⚠️  Migration 013 already applied!")
        response = input("Do you want to re-run it anyway? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        # Delete existing entry
        cursor.execute("DELETE FROM schema_version WHERE version = 13;")
        conn.commit()

    # Execute migration
    print("\n🚀 Executing migration 013...")
    cursor.execute(migration_sql)
    conn.commit()

    print("✅ Migration 013 executed successfully!")

    # Verify
    print("\nVerifying schema changes...")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'user'
        AND column_name IN ('profile_picture', 'location', 'bio')
        ORDER BY column_name;
    """)

    columns = cursor.fetchall()
    if columns:
        print("\n✅ New columns added to user table:")
        for col_name, data_type in columns:
            print(f"  - {col_name} ({data_type})")
    else:
        print("\n⚠️  Warning: Could not verify new columns")

    # Check updated schema version
    print("\nUpdated schema versions:")
    cursor.execute("SELECT version, description, applied_at FROM schema_version ORDER BY version DESC LIMIT 5;")
    updated_versions = cursor.fetchall()
    for version, description, applied_at in updated_versions:
        print(f"  Version {version}: {description} (applied {applied_at})")

    cursor.close()
    conn.close()

    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("1. Deploy updated Chatter application with new dependencies")
    print("2. Set environment variables: NAS_HOST, NAS_USERNAME, NAS_PASSWORD")
    print("3. Test profile endpoints: /profile/{username}, /profile/picture")

except Exception as e:
    print(f"\n❌ Error executing migration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
