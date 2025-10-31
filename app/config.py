"""
Configuration settings for Chatter application.
Environment variables should be used for sensitive values.
"""
import os
from pathlib import Path

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://chatter_user:chatter_pass@localhost:5432/chatter")

# CORS origins
CORS_ORIGINS = [
    "https://kevsrobots.com",
    "https://www.kevsrobots.com",
    "http://0.0.0.0:4000",  # Local Jekyll development
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

# Session configuration
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "change-me-in-production")
SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds

# Profile picture storage configuration
# NAS storage settings (credentials from environment variables)
NAS_HOST = os.getenv("NAS_HOST", "192.168.1.79")
NAS_USERNAME = os.getenv("NAS_USERNAME")  # Must be set in environment
NAS_PASSWORD = os.getenv("NAS_PASSWORD")  # Must be set in environment
NAS_SHARE_NAME = os.getenv("NAS_SHARE_NAME", "chatter")  # SMB share name
NAS_PROFILE_PICTURES_PATH = "profile_pictures"  # Path within the share

# Local fallback storage (if NAS is unavailable)
LOCAL_STORAGE_PATH = Path("/tmp/chatter_uploads")
LOCAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Image upload constraints
MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
PROFILE_PICTURE_DIMENSIONS = (400, 400)  # Max width, max height

# URL configuration
PROFILE_PICTURE_URL_BASE = "/profile_pictures"  # URL path to serve images
