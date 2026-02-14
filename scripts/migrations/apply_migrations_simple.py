#!/usr/bin/env python3
"""
Simple migration runner - executes SQL files directly
"""
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

def run_sql_file(filepath: Path):
    """Execute a SQL file"""
    print(f"\n{'='*80}")
    print(f"Running: {filepath.name}")
    print(f"{'='*80}")

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False

    engine = create_engine(DATABASE_URL)

    try:
        with open(filepath, 'r') as f:
            sql = f.read()

        # Remove comment-only lines
        lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
        sql = '\n'.join(lines)

        with engine.begin() as conn:  # Auto-commit transaction
            conn.execute(text(sql))

        print(f"✅ Successfully executed {filepath.name}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    migrations_dir = Path(__file__).parent / 'migrations' / 'versions'

    files = [
        migrations_dir / '016_create_user_projects.sql',
        migrations_dir / '017_extend_likes_comments_for_entities.sql'
    ]

    print("🚀 Running User Projects Migrations")
    success_count = 0

    for filepath in files:
        if run_sql_file(filepath):
            success_count += 1

    print(f"\n{'='*80}")
    print(f"✨ {success_count}/{len(files)} migrations successful")
    print(f"{'='*80}")

    # Show schema versions
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT version, description, applied_at FROM schema_version "
            "WHERE version ~ '^[0-9]+$' ORDER BY CAST(version AS INTEGER) DESC LIMIT 5"
        ))
        print("\n📋 Recent schema versions:")
        for row in result:
            print(f"  {row[0]:>3} | {row[1]:60} | {row[2]}")

    return success_count == len(files)

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
