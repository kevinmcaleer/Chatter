#!/usr/bin/env python3
"""
Refresh the page_view_counts materialized view
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

def refresh_materialized_view():
    """Refresh the page_view_counts materialized view"""
    print("=" * 60)
    print("Refreshing page_view_counts Materialized View")
    print("=" * 60)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("\nRefreshing materialized view...")
        cur.execute("REFRESH MATERIALIZED VIEW page_view_counts;")
        conn.commit()

        print("✅ Materialized view refreshed successfully!")

        # Check the results
        print("\n" + "=" * 60)
        print("Top 20 Most Viewed Pages (after refresh)")
        print("=" * 60)
        cur.execute("""
            SELECT url, view_count, unique_visitors, last_viewed_at
            FROM page_view_counts
            ORDER BY view_count DESC
            LIMIT 20;
        """)
        rows = cur.fetchall()
        for i, (url, views, unique, last_viewed) in enumerate(rows, 1):
            print(f"{i:2}. {url}")
            print(f"    Views: {views}, Unique visitors: {unique}")
            print(f"    Last viewed: {last_viewed}")
            print()

        # Check the top_viewed_pages view
        print("=" * 60)
        print("Top 10 from top_viewed_pages view")
        print("=" * 60)
        cur.execute("SELECT url, view_count, unique_visitors FROM top_viewed_pages;")
        rows = cur.fetchall()
        for i, (url, views, unique) in enumerate(rows, 1):
            print(f"{i:2}. {url}: {views} views ({unique} unique)")

        cur.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ Done!")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    refresh_materialized_view()
