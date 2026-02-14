#!/usr/bin/env python3
"""Apply migration 019: Rename tables to plural naming convention"""
import psycopg2
import sys
from pathlib import Path

# Database credentials
DB_HOST = "192.168.2.3"
DB_PORT = "5433"
DB_NAME = "kevsrobots_cms"
DB_USER = "Hd4AZn:NlSpH"
DB_PASSWORD = "8&0+6849Mx#S"

def apply_migration():
    """Apply migration 019"""
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "versions" / "019_rename_tables_to_plural.sql"

    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        return False

    print("=" * 70)
    print("Applying Migration 019: Rename Tables to Plural")
    print("=" * 70)
    print()

    try:
        # Connect to database
        print(f"Connecting to {DB_NAME} on {DB_HOST}:{DB_PORT}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = False
        cur = conn.cursor()

        print("✓ Connected")
        print()

        # Check current schema version
        cur.execute("SELECT MAX(version::integer) FROM schema_version WHERE version ~ '^[0-9]+$';")
        current_version = cur.fetchone()[0] or 0
        print(f"Current schema version: {current_version}")

        if current_version >= 19:
            print("✗ Migration 019 already applied")
            conn.close()
            return False

        # Read migration file
        print(f"Reading migration file: {migration_file.name}")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Show what will be renamed
        print()
        print("Tables to be renamed:")
        print("  user          → users")
        print("  comment       → comments")
        print("  like          → likes")
        print("  pageview      → page_views")
        print("  commentlike   → comment_likes")
        print("  excluded_ip   → excluded_ips")
        print("  and others...")
        print()

        # Confirm
        response = input("Apply this migration? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled")
            conn.close()
            return False

        # Apply migration
        print()
        print("Applying migration...")
        try:
            cur.execute(migration_sql)
            conn.commit()
            print("✓ Migration applied successfully")
            print()

            # Verify
            cur.execute("SELECT MAX(version) FROM schema_version;")
            new_version = cur.fetchone()[0]
            print(f"New schema version: {new_version}")

            # Check renamed tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'comments', 'likes', 'page_views', 'comment_likes', 'excluded_ips')
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]

            if len(tables) == 6:
                print("✓ All expected tables renamed successfully:")
                for table in tables:
                    print(f"  • {table}")
            else:
                print(f"⚠ Warning: Expected 6 renamed tables, found {len(tables)}")

        except Exception as e:
            print(f"✗ Error applying migration: {e}")
            conn.rollback()
            cur.close()
            conn.close()
            return False

        cur.close()
        conn.close()

        print()
        print("=" * 70)
        print("Migration Complete!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Restart Chatter applications on all servers")
        print("2. Test the website to verify comments and page views work")
        print()
        print("To rollback if needed:")
        print("  psql -h 192.168.2.3 -p 5433 -U 'Hd4AZn:NlSpH' -d kevsrobots_cms \\")
        print("    -f migrations/versions/019_rename_tables_to_plural_rollback.sql")
        print()

        return True

    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
