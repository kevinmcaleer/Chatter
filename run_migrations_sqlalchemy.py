#!/usr/bin/env python3
"""
Run database migrations for Issues #43 and #69 using SQLAlchemy
Reads database credentials from .env file
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

def run_migration(migration_file):
    """Run a SQL migration file"""
    print(f"\n{'='*80}")
    print(f"Running migration: {migration_file.name}")
    print(f"{'='*80}\n")

    # Read migration file
    with open(migration_file, 'r') as f:
        sql = f.read()

    # Connect and execute
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        try:
            # Execute the entire SQL file as one transaction
            # Split into statements but preserve structure
            print(f"Executing migration SQL...")

            # Use raw connection to execute multiple statements
            result = conn.connection.cursor()
            result.execute(sql)
            conn.connection.commit()

            print(f"\n✅ Migration completed successfully: {migration_file.name}")
        except Exception as e:
            print(f"\n❌ Error running migration: {e}")
            conn.connection.rollback()
            raise

def main():
    migrations_dir = Path(__file__).parent / "migrations" / "versions"

    # Run migrations in order
    migrations = [
        migrations_dir / "014_add_comment_likes.sql",
        migrations_dir / "015_add_comment_replies.sql"
    ]

    for migration_file in migrations:
        if migration_file.exists():
            run_migration(migration_file)
        else:
            print(f"⚠️  Migration file not found: {migration_file}")

    print(f"\n{'='*80}")
    print("✅ All migrations completed successfully!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
