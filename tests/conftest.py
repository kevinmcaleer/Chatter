import os
import pytest

# Monkey-patch load_dotenv to prevent loading .env during tests
import dotenv
_original_load_dotenv = dotenv.load_dotenv
def _mock_load_dotenv(*args, **kwargs):
    pass  # Do nothing - don't load .env file
dotenv.load_dotenv = _mock_load_dotenv

# Set up test environment variables before importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-not-for-production"
os.environ["ENVIRONMENT"] = "testing"
# Don't set DATABASE_URL - let database.py fall back to SQLite

# Now safe to import pytest fixtures and other test utilities
