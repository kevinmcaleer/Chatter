#!/usr/bin/env python3
"""Apply migration 019 automatically (no prompts)"""
import psycopg2
import sys
from pathlib import Path

DB_HOST = "192.168.2.3"
DB_PORT = "5433"
DB_NAME = "kevsrobots_cms"
DB_USER = "Hd4AZn:NlSpH"
DB_PASSWORD = "8&0+6849Mx#S"

def apply_migration():
    """Apply migration 019"""
    print("=" * 70)
    print("Applying Migration 019: Rename Tables to Plural")
    print("=" * 70)
    print()

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = False
        cur = conn.cursor()

        print("✓ Connected to database")

        # Check current schema version
        cur.execute("SELECT MAX(version::integer) FROM schema_version WHERE version ~ '^[0-9]+$';")
        current_version = cur.fetchone()[0] or 0
        print(f"Current schema version: {current_version}")

        if current_version >= 19:
            print("Migration 019 already applied")
            conn.close()
            return True

        print()
        print("Renaming tables...")

        # Apply renames
        renames = [
            ('"user"', 'users'),
            ('comment', 'comments'),
            ('"like"', 'likes'),
            ('pageview', 'page_views'),
            ('commentlike', 'comment_likes'),
            ('excluded_ip', 'excluded_ips'),
            ('commentversion', 'comment_versions'),
            ('project_file', 'project_files'),
            ('project_step', 'project_steps'),
            ('project_image', 'project_images'),
            ('project_link', 'project_links'),
            ('project_tag', 'project_tags'),
            ('project_component', 'project_components'),
            ('accountlog', 'account_logs'),
        ]

        for old_name, new_name in renames:
            try:
                cur.execute(f"ALTER TABLE IF EXISTS {old_name} RENAME TO {new_name};")
                print(f"  ✓ {old_name:25s} → {new_name}")
            except Exception as e:
                print(f"  ✗ {old_name:25s} → {new_name}: {e}")

        # Update schema version
        cur.execute("""
            INSERT INTO schema_version (version, description, applied_at)
            VALUES ('19', 'Rename tables from singular to plural naming convention', NOW());
        """)

        conn.commit()

        print()
        print("✓ Migration applied successfully")

        # Verify
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('users', 'comments', 'likes', 'page_views', 'comment_likes', 'excluded_ips')
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]

        print()
        print(f"Verified {len(tables)}/6 core tables renamed:")
        for table in tables:
            print(f"  • {table}")

        cur.close()
        conn.close()

        print()
        print("=" * 70)
        print("Migration Complete!")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
