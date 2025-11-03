#!/usr/bin/env python3
"""
Run database migrations for Issues #43 and #69 using SQLAlchemy
"""
from pathlib import Path
from sqlalchemy import create_engine, text

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
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        try:
            # Execute each statement (split by semicolons, filter out comments)
            statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

            for statement in statements:
                if statement:
                    print(f"Executing: {statement[:100]}...")
                    conn.execute(text(statement))

            conn.commit()
            print(f"\n✅ Migration completed successfully: {migration_file.name}")
        except Exception as e:
            print(f"\n❌ Error running migration: {e}")
            conn.rollback()
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
