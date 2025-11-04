#!/usr/bin/env python3
"""
Migration script to move profile pictures from local container storage to NAS.

This script:
1. Connects to each production server (dev01, dev03, dev04)
2. Extracts profile pictures from /tmp/chatter_uploads/profile_pictures/
3. Uploads them to NAS storage
4. Verifies all user profile pictures are accessible

Usage:
    python migrate_profile_pictures_to_nas.py

Prerequisites:
    - SSH access to production servers
    - NAS credentials configured in .env
    - smbprotocol package installed (pip install smbprotocol)
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Set
import subprocess
import tempfile
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import NAS functions
sys.path.insert(0, str(Path(__file__).parent / "app"))
from storage import save_to_nas, check_nas_connection
from config import NAS_HOST, NAS_USERNAME, NAS_PASSWORD, NAS_SHARE_NAME

# Production servers
PRODUCTION_SERVERS = [
    "192.168.2.1",  # dev01
    "192.168.2.3",  # dev03
    "192.168.2.4",  # dev04
]

CONTAINER_NAME = "chatter-app"
CONTAINER_PATH = "/tmp/chatter_uploads/profile_pictures"


def check_prerequisites() -> bool:
    """Check if all prerequisites are met."""
    logger.info("Checking prerequisites...")

    # Check NAS credentials
    if not all([NAS_HOST, NAS_USERNAME, NAS_PASSWORD, NAS_SHARE_NAME]):
        logger.error("NAS credentials not configured. Check .env file.")
        return False

    logger.info(f"NAS Host: {NAS_HOST}")
    logger.info(f"NAS Share: {NAS_SHARE_NAME}")
    logger.info(f"NAS Username: {NAS_USERNAME}")

    # Check NAS connection
    if not check_nas_connection():
        logger.error("Cannot connect to NAS. Check credentials and network.")
        return False

    logger.info("✓ NAS connection successful")
    return True


def get_files_from_container(server: str) -> List[str]:
    """
    Get list of profile picture files from a production server's container.

    Args:
        server: Server IP address

    Returns:
        List of filenames
    """
    logger.info(f"Checking {server} for profile pictures...")

    try:
        # Check if container exists and has files
        cmd = [
            "ssh", f"kev@{server}",
            f"docker exec {CONTAINER_NAME} ls -1 {CONTAINER_PATH} 2>/dev/null || true"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.warning(f"Could not list files on {server}: {result.stderr}")
            return []

        files = [f.strip() for f in result.stdout.split('\n') if f.strip() and f.strip().endswith('.png')]
        logger.info(f"Found {len(files)} files on {server}")
        return files

    except Exception as e:
        logger.error(f"Error accessing {server}: {e}")
        return []


def download_file_from_container(server: str, filename: str, temp_dir: Path) -> Path:
    """
    Download a file from container to local temp directory.

    Args:
        server: Server IP address
        filename: Filename to download
        temp_dir: Temporary directory to save to

    Returns:
        Path to downloaded file
    """
    local_path = temp_dir / filename
    remote_path = f"{CONTAINER_PATH}/{filename}"

    try:
        # Use docker cp via ssh
        cmd = [
            "ssh", f"kev@{server}",
            f"docker cp {CONTAINER_NAME}:{remote_path} -"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60
        )

        if result.returncode == 0:
            local_path.write_bytes(result.stdout)
            logger.info(f"Downloaded {filename} from {server} ({len(result.stdout)} bytes)")
            return local_path
        else:
            logger.error(f"Failed to download {filename} from {server}")
            return None

    except Exception as e:
        logger.error(f"Error downloading {filename} from {server}: {e}")
        return None


def migrate_files():
    """Main migration function."""
    logger.info("=" * 60)
    logger.info("Profile Picture Migration: Container -> NAS")
    logger.info("=" * 60)

    if not check_prerequisites():
        logger.error("Prerequisites check failed. Exiting.")
        return False

    # Collect all unique filenames from all servers
    all_files: Set[str] = set()

    for server in PRODUCTION_SERVERS:
        files = get_files_from_container(server)
        all_files.update(files)

    if not all_files:
        logger.warning("No profile pictures found on any server.")
        logger.info("This is expected if no users have uploaded profile pictures yet.")
        return True

    logger.info(f"\nFound {len(all_files)} unique profile pictures across all servers")
    logger.info("=" * 60)

    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        migrated_count = 0
        failed_count = 0

        for filename in sorted(all_files):
            logger.info(f"\nMigrating: {filename}")

            # Try to download from each server until successful
            file_content = None
            for server in PRODUCTION_SERVERS:
                local_path = download_file_from_container(server, filename, temp_path)
                if local_path and local_path.exists():
                    file_content = local_path.read_bytes()
                    break

            if not file_content:
                logger.error(f"✗ Could not download {filename} from any server")
                failed_count += 1
                continue

            # Upload to NAS
            if save_to_nas(file_content, filename):
                logger.info(f"✓ Successfully migrated {filename} to NAS")
                migrated_count += 1
            else:
                logger.error(f"✗ Failed to upload {filename} to NAS")
                failed_count += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Total files found: {len(all_files)}")
    logger.info(f"Successfully migrated: {migrated_count}")
    logger.info(f"Failed: {failed_count}")

    if failed_count == 0:
        logger.info("\n✓ All profile pictures migrated successfully!")
        return True
    else:
        logger.warning(f"\n⚠ {failed_count} files failed to migrate")
        return False


if __name__ == "__main__":
    try:
        success = migrate_files()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        sys.exit(1)
