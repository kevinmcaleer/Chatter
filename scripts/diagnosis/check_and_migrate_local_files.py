#!/usr/bin/env python3
"""
Check for local profile pictures and migrate them to NAS.

This script should be run INSIDE the Docker container on each production server:
    docker exec chatter-app python check_and_migrate_local_files.py

It will:
1. Check /tmp/chatter_uploads/profile_pictures/ for files
2. Upload any found files to NAS
3. Report results
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.storage import save_to_nas, check_nas_connection, LOCAL_STORAGE_PATH
from app.config import NAS_HOST, NAS_SHARE_NAME


def migrate_local_files():
    """Check for and migrate local profile pictures to NAS."""
    logger.info("=" * 60)
    logger.info("Profile Picture Migration Check")
    logger.info("=" * 60)

    # Check local storage path
    local_pics_dir = LOCAL_STORAGE_PATH / "profile_pictures"

    if not local_pics_dir.exists():
        logger.info(f"✓ No local storage directory found at {local_pics_dir}")
        logger.info("  This is expected - no migration needed!")
        return True

    # List files
    files = list(local_pics_dir.glob("*.png"))

    if not files:
        logger.info(f"✓ Local directory exists but is empty: {local_pics_dir}")
        logger.info("  No migration needed!")
        return True

    logger.info(f"Found {len(files)} profile pictures in local storage")
    logger.info(f"Location: {local_pics_dir}")
    logger.info("")

    # Check NAS connection
    if not check_nas_connection():
        logger.error("✗ Cannot connect to NAS - migration aborted")
        logger.error(f"  NAS: {NAS_HOST}/{NAS_SHARE_NAME}")
        logger.error("  Check credentials and network connectivity")
        return False

    logger.info(f"✓ NAS connection successful: {NAS_HOST}/{NAS_SHARE_NAME}")
    logger.info("")

    # Migrate each file
    migrated = 0
    failed = 0

    for file_path in files:
        filename = file_path.name
        logger.info(f"Migrating: {filename}")

        try:
            # Read file content
            file_content = file_path.read_bytes()

            # Upload to NAS
            if save_to_nas(file_content, filename):
                logger.info(f"  ✓ Uploaded to NAS ({len(file_content)} bytes)")
                migrated += 1
            else:
                logger.error(f"  ✗ Upload failed")
                failed += 1

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            failed += 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Total files found: {len(files)}")
    logger.info(f"Successfully migrated: {migrated}")
    logger.info(f"Failed: {failed}")

    if failed == 0:
        logger.info("")
        logger.info("✓ All files migrated successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Verify files on NAS: smbclient //192.168.1.79/chatter -U kevsrobots")
        logger.info("  2. Local files are still in /tmp (will be lost on restart)")
        logger.info("  3. Future uploads will go directly to NAS")
        return True
    else:
        logger.warning("")
        logger.warning(f"⚠ {failed} files failed to migrate")
        logger.warning("  Check NAS permissions and disk space")
        return False


if __name__ == "__main__":
    try:
        success = migrate_local_files()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)
