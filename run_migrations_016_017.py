#!/usr/bin/env python3
"""
Run migrations 016 and 017 for User Projects feature
- Migration 016: Create user projects tables
- Migration 017: Extend likes/comments for entity support
"""
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

def check_migration_applied(conn, version: int) -> bool:
    """Check if a migration has already been applied"""
    result = conn.execute(
        text("SELECT COUNT(*) FROM schema_version WHERE version = :version"),
        {"version": str(version)}
    ).scalar()
    return result > 0

def run_migration(migration_file: Path, version: int, description: str):
    """Run a migration SQL file"""
    print(f"\n{'='*80}")
    print(f"Running Migration {version}: {description}")
    print(f"{'='*80}")

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if already applied
            if check_migration_applied(conn, version):
                print(f"⚠️  Migration {version} already applied. Skipping.")
                return True

            # Read SQL file
            with open(migration_file, 'r') as f:
                sql_content = f.read()

            # Split by semicolons and execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

            print(f"📄 Executing {len(statements)} SQL statements...")

            for i, statement in enumerate(statements, 1):
                # Skip INSERT INTO schema_version as we'll add it separately
                if 'INSERT INTO schema_version' in statement:
                    continue

                try:
                    conn.execute(text(statement))
                    print(f"  ✓ Statement {i}/{len(statements)} executed")
                except Exception as e:
                    print(f"  ✗ Statement {i} failed: {e}")
                    print(f"  Statement: {statement[:100]}...")
                    raise

            # Commit transaction
            conn.commit()
            print(f"✅ Migration {version} completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Migration {version} failed: {e}")
        return False

def main():
    """Run all pending migrations"""
    migrations_dir = Path(__file__).parent / 'migrations' / 'versions'

    migrations = [
        {
            'version': 16,
            'description': 'Create user projects tables',
            'file': migrations_dir / '016_create_user_projects.sql'
        },
        {
            'version': 17,
            'description': 'Extend likes/comments for entity support',
            'file': migrations_dir / '017_extend_likes_comments_for_entities.sql'
        }
    ]

    print("🚀 Starting User Projects Migrations")
    print(f"📁 Migrations directory: {migrations_dir}")
    print(f"🗄️  Database: {DATABASE_URL.split('@')[1]}")  # Hide credentials

    success_count = 0
    for migration in migrations:
        if run_migration(migration['file'], migration['version'], migration['description']):
            success_count += 1

    print(f"\n{'='*80}")
    print(f"✨ Migration Summary: {success_count}/{len(migrations)} successful")
    print(f"{'='*80}")

    # Show current schema versions
    print("\n📋 Current schema versions:")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT version, description, applied_at FROM schema_version WHERE version ~ '^[0-9]+$' ORDER BY CAST(version AS INTEGER) DESC LIMIT 5")
        )
        for row in result:
            print(f"  {row[0]:>3} | {row[1]:60} | {row[2]}")

    return success_count == len(migrations)

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
