#!/usr/bin/env python3
"""
Apply migration 012: Fix top viewed pages view to query pageview directly
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
    """Apply migration 012"""
    print("=" * 60)
    print("Applying Migration 012: Fix top_viewed_pages view")
    print("=" * 60)

    try:
        # Read migration file
        migration_file = 'migrations/versions/012_fix_top_viewed_pages_view.sql'
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        print(f"\nConnecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Apply the migration
        print(f"Recreating top_viewed_pages view to query pageview table directly...")
        cur.execute(migration_sql)
        conn.commit()

        print("✅ Migration applied successfully!")

        # Verify the view works
        print("\n" + "=" * 60)
        print("Testing top_viewed_pages view (should now be real-time)")
        print("=" * 60)

        cur.execute("SELECT url, view_count, unique_visitors FROM top_viewed_pages;")
        rows = cur.fetchall()

        print("\nTop 10 Most Viewed Pages:")
        for i, (url, views, unique) in enumerate(rows, 1):
            print(f"{i:2}. {url}")
            print(f"    Views: {views}, Unique visitors: {unique}")

        # Record migration in schema_version table
        cur.execute("""
            INSERT INTO schema_version (version, description)
            VALUES ('012', 'Fix top_viewed_pages view to query pageview table directly for real-time data')
            ON CONFLICT (version) DO NOTHING;
        """)
        conn.commit()

        print("\n✅ Migration recorded in schema_version table")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ Migration 012 completed successfully!")
        print("=" * 60)
        print("\nThe top_viewed_pages view now queries pageview table directly")
        print("and will always show real-time data without needing refresh!")

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
