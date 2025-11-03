#!/usr/bin/env python3
"""
Update schema_version table after running migrations
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

def add_migration_to_schema_version(version: str, description: str):
    """Add a migration to the schema_version table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if version already exists
        result = conn.execute(
            text("SELECT COUNT(*) FROM schema_version WHERE version = :version"),
            {"version": version}
        ).scalar()

        if result > 0:
            print(f"⚠️  Migration {version} already exists in schema_version")
            return False

        # Insert new version
        conn.execute(
            text("""
                INSERT INTO schema_version (version, description, applied_at)
                VALUES (:version, :description, NOW())
            """),
            {"version": version, "description": description}
        )
        conn.commit()
        print(f"✅ Added migration {version}: {description}")
        return True

def view_schema_versions():
    """Display all schema versions"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT version, description, applied_at FROM schema_version WHERE version ~ '^[0-9]+$' ORDER BY CAST(version AS INTEGER)")
        )

        print("\nCurrent schema versions:")
        print("-" * 100)
        for row in result:
            print(f"  {row[0]:>3} | {row[1]:60} | {row[2]}")
        print("-" * 100)

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        # No arguments, just view current versions
        view_schema_versions()
    elif len(sys.argv) == 3:
        # Add a new version
        version = sys.argv[1]
        description = sys.argv[2]
        add_migration_to_schema_version(version, description)
        view_schema_versions()
    else:
        print("Usage:")
        print("  python3 update_schema_version.py                                    # View current versions")
        print("  python3 update_schema_version.py <version> <description>            # Add new version")
        print("\nExample:")
        print("  python3 update_schema_version.py 016 'Add new feature'")
