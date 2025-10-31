"""
Storage utilities for handling file uploads to NAS or local storage.
Supports SMB/CIFS shares for NAS storage with local fallback.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io
import uuid

from .config import (
    NAS_HOST,
    NAS_USERNAME,
    NAS_PASSWORD,
    NAS_SHARE_NAME,
    NAS_PROFILE_PICTURES_PATH,
    LOCAL_STORAGE_PATH,
    MAX_PROFILE_PICTURE_SIZE,
    ALLOWED_IMAGE_EXTENSIONS,
    PROFILE_PICTURE_DIMENSIONS,
)

logger = logging.getLogger(__name__)

# Track NAS availability
_nas_available = None


def check_nas_connection() -> bool:
    """
    Check if NAS is available and credentials are configured.
    Caches result to avoid repeated connection attempts.
    """
    global _nas_available

    if _nas_available is not None:
        return _nas_available

    if not all([NAS_HOST, NAS_USERNAME, NAS_PASSWORD, NAS_SHARE_NAME]):
        logger.warning("NAS credentials not fully configured, using local storage")
        _nas_available = False
        return False

    try:
        # Try to import smbprotocol for NAS access
        from smbprotocol.connection import Connection
        from smbprotocol.session import Session

        connection = Connection(uuid.uuid4(), NAS_HOST, 445)
        connection.connect(timeout=5)

        session = Session(connection, NAS_USERNAME, NAS_PASSWORD)
        session.connect()

        # Success - NAS is available
        _nas_available = True
        logger.info(f"Successfully connected to NAS at {NAS_HOST}")

        # Close connection
        connection.disconnect()
        return True

    except ImportError:
        logger.error("smbprotocol not installed. Install with: pip install smbprotocol")
        _nas_available = False
        return False
    except Exception as e:
        logger.error(f"Failed to connect to NAS: {e}")
        _nas_available = False
        return False


def validate_image(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded image file.

    Args:
        file_content: Raw file bytes
        filename: Original filename

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"

    # Check file size
    if len(file_content) > MAX_PROFILE_PICTURE_SIZE:
        max_mb = MAX_PROFILE_PICTURE_SIZE / (1024 * 1024)
        return False, f"File too large. Maximum size: {max_mb}MB"

    # Verify it's actually an image
    try:
        img = Image.open(io.BytesIO(file_content))
        img.verify()  # Verify it's a valid image
        return True, None
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def resize_image(file_content: bytes, max_width: int, max_height: int) -> bytes:
    """
    Resize image to fit within max dimensions while maintaining aspect ratio.

    Args:
        file_content: Raw image bytes
        max_width: Maximum width
        max_height: Maximum height

    Returns:
        Resized image bytes (PNG format)
    """
    img = Image.open(io.BytesIO(file_content))

    # Convert RGBA to RGB if necessary (for JPEG compatibility)
    if img.mode == 'RGBA':
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
        img = background

    # Resize maintaining aspect ratio
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    output.seek(0)
    return output.read()


def generate_unique_filename(original_filename: str, user_id: int) -> str:
    """
    Generate a unique filename for profile picture.

    Args:
        original_filename: Original uploaded filename
        user_id: User ID

    Returns:
        Unique filename with format: user_{id}_{uuid}.png
    """
    unique_id = uuid.uuid4().hex[:8]
    return f"user_{user_id}_{unique_id}.png"


def save_to_nas(file_content: bytes, filename: str) -> bool:
    """
    Save file to NAS storage via SMB.

    Args:
        file_content: File bytes to save
        filename: Destination filename

    Returns:
        True if successful, False otherwise
    """
    try:
        from smbprotocol.connection import Connection
        from smbprotocol.session import Session
        from smbprotocol.tree import TreeConnect
        from smbprotocol.file import Open, CreateDisposition, FileAccess

        # Connect to NAS
        connection = Connection(uuid.uuid4(), NAS_HOST, 445)
        connection.connect(timeout=10)

        session = Session(connection, NAS_USERNAME, NAS_PASSWORD)
        session.connect()

        # Connect to share
        tree = TreeConnect(session, f"\\\\{NAS_HOST}\\{NAS_SHARE_NAME}")
        tree.connect()

        # Ensure directory exists (create if needed)
        try:
            dir_open = Open(tree, NAS_PROFILE_PICTURES_PATH)
            dir_open.create(
                access=FileAccess.FILE_READ_ATTRIBUTES,
                disposition=CreateDisposition.FILE_OPEN_IF
            )
            dir_open.close()
        except Exception as e:
            logger.warning(f"Could not create directory on NAS: {e}")

        # Write file
        file_path = f"{NAS_PROFILE_PICTURES_PATH}\\{filename}"
        file_open = Open(tree, file_path)
        file_open.create(
            access=FileAccess.FILE_WRITE_DATA,
            disposition=CreateDisposition.FILE_OVERWRITE_IF
        )
        file_open.write(file_content, 0)
        file_open.close()

        # Cleanup
        tree.disconnect()
        connection.disconnect()

        logger.info(f"Successfully saved {filename} to NAS")
        return True

    except Exception as e:
        logger.error(f"Failed to save to NAS: {e}")
        return False


def save_to_local(file_content: bytes, filename: str) -> bool:
    """
    Save file to local storage as fallback.

    Args:
        file_content: File bytes to save
        filename: Destination filename

    Returns:
        True if successful, False otherwise
    """
    try:
        profile_pics_dir = LOCAL_STORAGE_PATH / "profile_pictures"
        profile_pics_dir.mkdir(parents=True, exist_ok=True)

        file_path = profile_pics_dir / filename
        file_path.write_bytes(file_content)

        logger.info(f"Saved {filename} to local storage at {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save to local storage: {e}")
        return False


def save_profile_picture(
    file_content: bytes,
    original_filename: str,
    user_id: int
) -> Optional[str]:
    """
    Save uploaded profile picture to NAS or local storage.

    Process:
    1. Validate image
    2. Resize to max dimensions
    3. Generate unique filename
    4. Try to save to NAS, fallback to local if unavailable
    5. Return filename on success, None on failure

    Args:
        file_content: Raw uploaded file bytes
        original_filename: Original filename from upload
        user_id: User ID for filename generation

    Returns:
        Filename if saved successfully, None otherwise
    """
    # Validate image
    is_valid, error_msg = validate_image(file_content, original_filename)
    if not is_valid:
        logger.error(f"Image validation failed: {error_msg}")
        return None

    # Resize image
    try:
        max_width, max_height = PROFILE_PICTURE_DIMENSIONS
        resized_content = resize_image(file_content, max_width, max_height)
    except Exception as e:
        logger.error(f"Failed to resize image: {e}")
        return None

    # Generate unique filename
    filename = generate_unique_filename(original_filename, user_id)

    # Try to save to NAS first
    if check_nas_connection():
        if save_to_nas(resized_content, filename):
            return filename
        else:
            logger.warning("NAS save failed, trying local storage...")

    # Fallback to local storage
    if save_to_local(resized_content, filename):
        return filename

    logger.error("Failed to save profile picture to both NAS and local storage")
    return None


def delete_profile_picture(filename: str) -> bool:
    """
    Delete profile picture from storage.

    Args:
        filename: Filename to delete

    Returns:
        True if deleted (or doesn't exist), False on error
    """
    success = False

    # Try to delete from NAS
    if check_nas_connection():
        try:
            from smbprotocol.connection import Connection
            from smbprotocol.session import Session
            from smbprotocol.tree import TreeConnect
            from smbprotocol.file import Open, CreateDisposition

            connection = Connection(uuid.uuid4(), NAS_HOST, 445)
            connection.connect(timeout=10)

            session = Session(connection, NAS_USERNAME, NAS_PASSWORD)
            session.connect()

            tree = TreeConnect(session, f"\\\\{NAS_HOST}\\{NAS_SHARE_NAME}")
            tree.connect()

            file_path = f"{NAS_PROFILE_PICTURES_PATH}\\{filename}"
            file_open = Open(tree, file_path)
            file_open.create(disposition=CreateDisposition.FILE_OPEN)
            file_open.delete()
            file_open.close()

            tree.disconnect()
            connection.disconnect()

            logger.info(f"Deleted {filename} from NAS")
            success = True

        except Exception as e:
            logger.warning(f"Could not delete from NAS (may not exist): {e}")

    # Also try local storage
    try:
        file_path = LOCAL_STORAGE_PATH / "profile_pictures" / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted {filename} from local storage")
            success = True
    except Exception as e:
        logger.warning(f"Could not delete from local storage: {e}")

    return success
