#!/usr/bin/env python3
"""
Test NAS connectivity and file operations.

This script tests:
1. NAS connection
2. File upload
3. File read
4. File delete

Usage:
    docker exec chatter-app python test_nas_connection.py
"""

import sys
import logging
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Import with proper module path
from app.storage import check_nas_connection, save_to_nas, read_from_nas, delete_profile_picture
from app.config import NAS_HOST, NAS_USERNAME, NAS_PASSWORD, NAS_SHARE_NAME

def test_nas_connectivity():
    """Test NAS connection and file operations."""
    logger.info("=" * 60)
    logger.info("NAS Connectivity Test")
    logger.info("=" * 60)

    logger.info(f"NAS Host: {NAS_HOST}")
    logger.info(f"NAS Share: {NAS_SHARE_NAME}")
    logger.info(f"NAS Username: {NAS_USERNAME}")

    # Test 1: Connection
    logger.info("\n[Test 1] Testing NAS connection...")
    if not check_nas_connection():
        logger.error("✗ NAS connection failed")
        return False
    logger.info("✓ NAS connection successful")

    # Test 2: File upload
    logger.info("\n[Test 2] Testing file upload...")
    test_content = b"Test profile picture content - " + str(Path(__file__).stat().st_mtime).encode()
    test_filename = "test_upload.png"

    if not save_to_nas(test_content, test_filename):
        logger.error("✗ File upload failed")
        return False
    logger.info(f"✓ File uploaded successfully: {test_filename}")

    # Test 3: File read
    logger.info("\n[Test 3] Testing file read...")
    read_content = read_from_nas(test_filename)

    if not read_content:
        logger.error("✗ File read failed")
        return False

    if read_content != test_content:
        logger.error("✗ File content mismatch")
        logger.error(f"Expected: {test_content}")
        logger.error(f"Got: {read_content}")
        return False

    logger.info(f"✓ File read successfully ({len(read_content)} bytes)")

    # Test 4: Cleanup (delete test file)
    logger.info("\n[Test 4] Cleaning up test file...")
    if delete_profile_picture(test_filename):
        logger.info("✓ Test file deleted successfully")
    else:
        logger.warning("⚠ Could not delete test file (manual cleanup may be needed)")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("✓ All NAS tests passed!")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_nas_connectivity()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
