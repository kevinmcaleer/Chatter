import os
import pytest

# Set up test environment variables before importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-not-for-production"

# Now safe to import pytest fixtures and other test utilities
