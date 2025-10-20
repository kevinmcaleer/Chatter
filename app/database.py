from sqlmodel import SQLModel, Session, create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to SQLite for development/testing
    sqlite_file_name = "data/database.db"
    DATABASE_URL = f"sqlite:///{sqlite_file_name}"
    print(f"⚠️  Using SQLite database: {sqlite_file_name}")
    print("   Set DATABASE_URL environment variable to use PostgreSQL")
else:
    print(f"✅ Using PostgreSQL database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
