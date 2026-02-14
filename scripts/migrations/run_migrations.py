#!/usr/bin/env python3
"""
Run database migrations for Issues #43 and #69
"""
import psycopg2
from pathlib import Path

# Database connection
DATABASE_URL = "postgresql://kevsrobots_user:ChangeMe123@192.168.2.1:5433/kevsrobots_cms"

def run_migration(migration_file):
    """Run a SQL migration file"""
    print(f"\n{'='*80}")
    print(f"Running migration: {migration_file.name}")
    print(f"{'='*80}\n")

    # Read migration file
    with open(migration_file, 'r') as f:
        sql = f.read()

    # Connect and execute
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        print(f"✅ Migration completed successfully: {migration_file.name}")
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    migrations_dir = Path(__file__).parent / "migrations"

    # Run migrations in order
    migrations = [
        migrations_dir / "add_comment_likes.sql",
        migrations_dir / "add_comment_replies.sql"
    ]

    for migration_file in migrations:
        if migration_file.exists():
            run_migration(migration_file)
        else:
            print(f"⚠️  Migration file not found: {migration_file}")

    print(f"\n{'='*80}")
    print("All migrations completed!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
