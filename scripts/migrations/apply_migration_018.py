#!/usr/bin/env python3
"""
Apply migration 018: Add excluded IPs table for analytics filtering
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
    """Apply migration 018"""
    print("=" * 60)
    print("Applying Migration 018: Add excluded IPs table")
    print("=" * 60)

    try:
        # Read migration file
        migration_file = 'migrations/versions/018_add_excluded_ips.sql'
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        print(f"\nConnecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Apply the migration
        print("Creating excluded_ip table and updating views...")
        cur.execute(migration_sql)
        conn.commit()

        print("✅ Migration applied successfully!")

        # Verify the table and data
        print("\n" + "=" * 60)
        print("Verifying excluded_ip table")
        print("=" * 60)

        cur.execute("SELECT ip_pattern, description FROM excluded_ip ORDER BY id;")
        rows = cur.fetchall()

        print("\nExcluded IP patterns:")
        for pattern, description in rows:
            print(f"  - {pattern}: {description}")

        # Test the views
        print("\n" + "=" * 60)
        print("Testing top_viewed_pages view (now excludes developer IPs)")
        print("=" * 60)

        cur.execute("SELECT url, view_count, unique_visitors FROM top_viewed_pages LIMIT 5;")
        rows = cur.fetchall()

        if rows:
            print("\nTop 5 Most Viewed Pages (excluding dev IPs):")
            for i, (url, views, unique) in enumerate(rows, 1):
                print(f"{i:2}. {url}")
                print(f"    Views: {views}, Unique visitors: {unique}")
        else:
            print("\nNo page views found (or all were from excluded IPs)")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ Migration 018 completed successfully!")
        print("=" * 60)
        print("\nThe excluded_ip table now filters out developer and private IPs")
        print("from page view analytics. You can add more IPs with:")
        print("  INSERT INTO excluded_ip (ip_pattern, description)")
        print("  VALUES ('1.2.3.4', 'Description here');")

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
