from sqlmodel import SQLModel, Session, create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Configure engine based on database type and environment
engine_kwargs = {}

if not DATABASE_URL:
    # Fallback to SQLite for development/testing
    sqlite_file_name = "data/database.db"
    DATABASE_URL = f"sqlite:///{sqlite_file_name}"
    print(f"⚠️  Using SQLite database: {sqlite_file_name}")
    print("   Set DATABASE_URL environment variable to use PostgreSQL")
    engine_kwargs["echo"] = True  # Enable SQL logging for development
else:
    print(f"✅ Using PostgreSQL database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")

    # PostgreSQL production settings
    if ENVIRONMENT == "production":
        engine_kwargs.update({
            "echo": False,  # Disable SQL logging in production
            "pool_size": 20,  # Number of connections to keep in pool (increased from 10)
            "max_overflow": 30,  # Max connections beyond pool_size (increased from 20)
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 1800,  # Recycle connections after 30 minutes (reduced from 1 hour)
            "pool_timeout": 30,  # Timeout waiting for connection from pool
            "connect_args": {
                "connect_timeout": 10,  # Connection timeout in seconds
                "options": "-c statement_timeout=30000"  # Query timeout: 30 seconds
            }
        })
        print("   Production database settings enabled")
    else:
        engine_kwargs.update({
            "echo": True,  # Enable SQL logging for development
            "pool_size": 5,
            "max_overflow": 10,
        })

engine = create_engine(DATABASE_URL, **engine_kwargs)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
