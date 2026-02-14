#!/usr/bin/env python3
"""Check database schema and permissions for Chatter application"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database credentials
DB_HOST = "192.168.2.3"
DB_PORT = "5433"
DB_NAME = "kevsrobots_cms"
DB_USER = "Hd4AZn:NlSpH"
DB_PASSWORD = "8&0+6849Mx#S"

def check_database():
    """Check database schema and permissions"""
    print("=" * 70)
    print("Chatter Database Schema Check")
    print("=" * 70)
    print()

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print(f"✓ Connected to {DB_NAME} on {DB_HOST}:{DB_PORT}")
        print(f"✓ User: {DB_USER}")
        print()

        # Check Chatter-related tables
        print("=" * 70)
        print("Checking Chatter Tables")
        print("=" * 70)
        print()

        chatter_tables = [
            'users',
            'comments',
            'likes',
            'page_views',
            'comment_likes',
            'user_profiles',
            'projects',
            'project_files',
            'project_steps',
            'excluded_ips'
        ]

        cur.execute("""
            SELECT table_name,
                   pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)

        existing_tables = {}
        for row in cur.fetchall():
            existing_tables[row[0]] = row[1]

        print(f"Found {len(existing_tables)} tables in database:")
        print()

        # Check expected Chatter tables
        for table in chatter_tables:
            if table in existing_tables:
                # Get row count
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                    count = cur.fetchone()[0]
                    print(f"  ✓ {table:20s} - {count:6d} rows - {existing_tables[table]:>10s}")
                except Exception as e:
                    print(f"  ✗ {table:20s} - ERROR: {e}")
            else:
                print(f"  ✗ {table:20s} - MISSING")

        print()

        # Show all tables (including unexpected ones)
        unexpected_tables = set(existing_tables.keys()) - set(chatter_tables)
        if unexpected_tables:
            print("Additional tables found:")
            for table in sorted(unexpected_tables):
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                    count = cur.fetchone()[0]
                    print(f"  • {table:20s} - {count:6d} rows - {existing_tables[table]:>10s}")
                except Exception as e:
                    print(f"  • {table:20s} - ERROR: {e}")
            print()

        # Check views
        print("=" * 70)
        print("Checking Views")
        print("=" * 70)
        print()

        cur.execute("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        views = [row[0] for row in cur.fetchall()]
        if views:
            print(f"Found {len(views)} views:")
            for view in views:
                print(f"  • {view}")
        else:
            print("  ✗ No views found")
            print("  Expected views: most_liked_pages, top_viewed_pages")
        print()

        # Check user permissions
        print("=" * 70)
        print("Checking User Permissions")
        print("=" * 70)
        print()

        cur.execute(f"""
            SELECT grantee, table_name, privilege_type
            FROM information_schema.table_privileges
            WHERE grantee = '{DB_USER}'
            AND table_schema = 'public'
            ORDER BY table_name, privilege_type;
        """)

        permissions = {}
        for row in cur.fetchall():
            table = row[1]
            priv = row[2]
            if table not in permissions:
                permissions[table] = []
            permissions[table].append(priv)

        if permissions:
            print(f"User '{DB_USER}' has permissions on {len(permissions)} objects:")
            print()
            for table in sorted(permissions.keys()):
                privs = ', '.join(sorted(permissions[table]))
                print(f"  {table:25s} - {privs}")
        else:
            print(f"  ✗ User '{DB_USER}' has NO permissions!")
            print("  This is likely the problem!")
        print()

        # Check schema version
        print("=" * 70)
        print("Checking Schema Version")
        print("=" * 70)
        print()

        try:
            cur.execute("SELECT version, applied_at FROM schema_version ORDER BY applied_at DESC LIMIT 1;")
            result = cur.fetchone()
            if result:
                print(f"  Current schema version: {result[0]}")
                print(f"  Applied at: {result[1]}")
            else:
                print("  ✗ No schema version found")
        except Exception as e:
            print(f"  ✗ schema_version table not found or error: {e}")
        print()

        # Check for recent data
        print("=" * 70)
        print("Checking Recent Activity")
        print("=" * 70)
        print()

        if 'comments' in existing_tables:
            try:
                cur.execute("SELECT COUNT(*), MAX(created_at) FROM comments;")
                count, latest = cur.fetchone()
                print(f"  Comments: {count} total, latest: {latest}")
            except Exception as e:
                print(f"  Comments: Error - {e}")

        if 'likes' in existing_tables:
            try:
                cur.execute("SELECT COUNT(*), MAX(created_at) FROM likes;")
                count, latest = cur.fetchone()
                print(f"  Likes: {count} total, latest: {latest}")
            except Exception as e:
                print(f"  Likes: Error - {e}")

        if 'page_views' in existing_tables:
            try:
                cur.execute("SELECT COUNT(*), MAX(viewed_at) FROM page_views;")
                count, latest = cur.fetchone()
                print(f"  Page views: {count} total, latest: {latest}")
            except Exception as e:
                print(f"  Page views: Error - {e}")

        if 'users' in existing_tables:
            try:
                cur.execute("SELECT COUNT(*), MAX(created_at) FROM users;")
                count, latest = cur.fetchone()
                print(f"  Users: {count} total, latest: {latest}")
            except Exception as e:
                print(f"  Users: Error - {e}")

        print()

        # Test basic operations
        print("=" * 70)
        print("Testing Basic Operations")
        print("=" * 70)
        print()

        # Test SELECT
        test_results = []
        for table in ['users', 'comments', 'likes', 'page_views']:
            if table in existing_tables:
                try:
                    cur.execute(f'SELECT * FROM "{table}" LIMIT 1;')
                    test_results.append(f"  ✓ SELECT from {table}")
                except Exception as e:
                    test_results.append(f"  ✗ SELECT from {table}: {e}")

        for result in test_results:
            print(result)

        print()

        cur.close()
        conn.close()

        print("=" * 70)
        print("Diagnostic Complete")
        print("=" * 70)
        print()
        print("If tables are missing or permissions are wrong, you need to:")
        print("1. Restore the full database backup (not just data)")
        print("2. Run database migrations to create missing tables")
        print("3. Grant proper permissions to user 'Hd4AZn:NlSpH'")
        print()

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    check_database()
