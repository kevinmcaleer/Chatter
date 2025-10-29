#!/usr/bin/env python3
"""
Check pageview data to debug the top_viewed_pages view
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

def check_data():
    """Check pageview data"""
    print("=" * 60)
    print("Checking Pageview Data")
    print("=" * 60)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Check total pageviews
        print("\n1. Total pageviews in pageview table:")
        cur.execute("SELECT COUNT(*) FROM pageview;")
        total = cur.fetchone()[0]
        print(f"   Total: {total}")

        # Check for uno-q-tips
        print("\n2. Searching for 'uno-q-tips' in pageview table:")
        cur.execute("""
            SELECT url, COUNT(*) as count
            FROM pageview
            WHERE url LIKE '%uno-q-tips%'
            GROUP BY url
            ORDER BY count DESC;
        """)
        rows = cur.fetchall()
        if rows:
            for url, count in rows:
                print(f"   {url}: {count} views")
        else:
            print("   No matches found")

        # Check top 20 from raw pageview table
        print("\n3. Top 20 pages from pageview table (raw count):")
        cur.execute("""
            SELECT url, COUNT(*) as view_count
            FROM pageview
            GROUP BY url
            ORDER BY view_count DESC
            LIMIT 20;
        """)
        rows = cur.fetchall()
        for i, (url, count) in enumerate(rows, 1):
            print(f"   {i}. {url}: {count} views")

        # Check materialized view
        print("\n4. Checking page_view_counts materialized view:")
        cur.execute("SELECT COUNT(*) FROM page_view_counts;")
        mv_count = cur.fetchone()[0]
        print(f"   Total URLs in materialized view: {mv_count}")

        # Check top 20 from materialized view
        print("\n5. Top 20 from page_view_counts materialized view:")
        cur.execute("""
            SELECT url, view_count, unique_visitors, last_viewed_at
            FROM page_view_counts
            ORDER BY view_count DESC
            LIMIT 20;
        """)
        rows = cur.fetchall()
        for i, (url, views, unique, last_viewed) in enumerate(rows, 1):
            print(f"   {i}. {url}: {views} views, {unique} unique")

        # Check when materialized view was last refreshed
        print("\n6. Checking if materialized view needs refresh:")
        cur.execute("""
            SELECT
                (SELECT MAX(viewed_at) FROM pageview) as latest_pageview,
                (SELECT MAX(last_viewed_at) FROM page_view_counts) as latest_in_matview;
        """)
        latest_pv, latest_mv = cur.fetchone()
        print(f"   Latest pageview timestamp: {latest_pv}")
        print(f"   Latest in materialized view: {latest_mv}")

        if latest_pv != latest_mv:
            print("\n   ⚠️  MATERIALIZED VIEW IS OUT OF DATE!")
            print("   The materialized view needs to be refreshed.")
            print("\n   Run: REFRESH MATERIALIZED VIEW page_view_counts;")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    check_data()
