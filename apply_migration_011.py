#!/usr/bin/env python3
"""
Apply migration 011: Create top viewed pages view
"""

import os
import sys
from dotenv import load_dotenv

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

# Load environment variables
load_dotenv('.env')

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

def apply_migration():
    """Apply migration 011"""
    print("=" * 60)
    print("Applying Migration 011: Create top viewed pages view")
    print("=" * 60)

    try:
        # Read migration file
        migration_file = 'migrations/versions/011_create_top_viewed_pages_view.sql'
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        print(f"\nConnecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Check if page_view_counts materialized view exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM pg_matviews
                WHERE schemaname = 'public'
                AND matviewname = 'page_view_counts'
            );
        """)

        matview_exists = cur.fetchone()[0]

        if not matview_exists:
            print("WARNING: page_view_counts materialized view does not exist!")
            print("You may need to apply migration 008 first.")
            conn.close()
            sys.exit(1)

        print("Verified: page_view_counts materialized view exists")

        # Apply the migration
        print(f"\nExecuting migration...")
        cur.execute(migration_sql)
        conn.commit()

        print("Migration applied successfully!")

        # Verify the view was created
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.views
                WHERE table_schema = 'public'
                AND table_name = 'top_viewed_pages'
            );
        """)

        view_exists = cur.fetchone()[0]

        if view_exists:
            print("\nVerified: top_viewed_pages view created successfully")

            # Try to query the view
            cur.execute("SELECT COUNT(*) FROM top_viewed_pages;")
            count = cur.fetchone()[0]
            print(f"Current view contains {count} pages")

            if count > 0:
                print("\nTop viewed pages:")
                cur.execute("SELECT url, view_count, unique_visitors FROM top_viewed_pages;")
                rows = cur.fetchall()
                for i, (url, views, unique) in enumerate(rows, 1):
                    print(f"  {i}. {url}")
                    print(f"     Views: {views}, Unique visitors: {unique}")
        else:
            print("\nERROR: View was not created successfully")
            sys.exit(1)

        # Record migration in schema_version table
        cur.execute("""
            INSERT INTO schema_version (version, description)
            VALUES ('011', 'Create top viewed pages view')
            ON CONFLICT (version) DO NOTHING;
        """)
        conn.commit()

        print("\nMigration recorded in schema_version table")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)
        print("Migration 011 completed successfully!")
        print("=" * 60)
        print("\nYou can now query: SELECT * FROM top_viewed_pages;")

    except FileNotFoundError:
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    apply_migration()
