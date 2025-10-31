"""
User profile management endpoints.
Handles profile viewing, editing, and profile picture uploads.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime
from pathlib import Path

from .database import get_session
from .auth import get_current_user, get_optional_user
from .models import User, Comment
from .storage import save_profile_picture, delete_profile_picture, LOCAL_STORAGE_PATH
from .config import NAS_PROFILE_PICTURES_PATH, PROFILE_PICTURE_URL_BASE

router = APIRouter()


# Pydantic schemas for API responses
from pydantic import BaseModel

class ProfileResponse(BaseModel):
    username: str
    firstname: str
    lastname: str
    location: Optional[str]
    bio: Optional[str]
    profile_picture_url: Optional[str]
    created_at: datetime
    comment_count: int
    is_own_profile: bool

class ProfileUpdateRequest(BaseModel):
    location: Optional[str] = None
    bio: Optional[str] = None


def get_profile_picture_url(filename: Optional[str]) -> Optional[str]:
    """
    Get the URL for a profile picture filename.

    Args:
        filename: Profile picture filename stored in database

    Returns:
        Full URL to the profile picture, or None if no picture
    """
    if not filename:
        return None
    return f"{PROFILE_PICTURE_URL_BASE}/{filename}"


def get_account_age_string(created_at: datetime) -> str:
    """
    Get a human-readable string for account age.

    Args:
        created_at: Account creation timestamp

    Returns:
        String like "2 years", "5 months", "3 days", "12 hours"
    """
    now = datetime.utcnow()
    delta = now - created_at

    years = delta.days // 365
    if years > 0:
        return f"{years} year{'s' if years != 1 else ''}"

    months = delta.days // 30
    if months > 0:
        return f"{months} month{'s' if months != 1 else ''}"

    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days != 1 else ''}"

    hours = delta.seconds // 3600
    return f"{hours} hour{'s' if hours != 1 else ''}"


@router.get("/profile/{username}", response_model=ProfileResponse)
def view_profile(
    username: str,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    View a user's public profile.

    Shows:
    - Username, name
    - Profile picture (if set)
    - Location (if set)
    - Bio (if set)
    - Account age
    - Number of comments posted

    Args:
        username: Username of profile to view
        current_user: Optional currently logged-in user

    Returns:
        ProfileResponse with user details

    Raises:
        404: User not found or inactive
    """
    # Get user by username
    user = session.exec(
        select(User).where(User.username == username)
    ).first()

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    # Count user's comments (exclude removed/hidden)
    comment_count = session.exec(
        select(func.count(Comment.id))
        .where(Comment.user_id == user.id)
        .where(Comment.is_removed == False)
        .where(Comment.is_hidden == False)
    ).one()

    # Check if viewing own profile
    is_own_profile = current_user is not None and current_user.id == user.id

    return ProfileResponse(
        username=user.username,
        firstname=user.firstname,
        lastname=user.lastname,
        location=user.location,
        bio=user.bio,
        profile_picture_url=get_profile_picture_url(user.profile_picture),
        created_at=user.created_at,
        comment_count=comment_count,
        is_own_profile=is_own_profile
    )


@router.get("/profile/me")
def view_own_profile(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    View your own profile (redirects to /profile/{username}).

    Requires authentication.

    Returns:
        ProfileResponse for current user
    """
    return view_profile(user.username, session, user)


@router.put("/profile")
def update_profile(
    profile_update: ProfileUpdateRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Update profile fields (location, bio).

    Requires authentication. Users can only update their own profile.

    Args:
        profile_update: Fields to update
        user: Current authenticated user

    Returns:
        Success message with updated fields
    """
    # Update fields if provided
    if profile_update.location is not None:
        user.location = profile_update.location.strip() if profile_update.location else None

    if profile_update.bio is not None:
        # Limit bio length
        bio = profile_update.bio.strip() if profile_update.bio else None
        if bio and len(bio) > 500:
            raise HTTPException(status_code=400, detail="Bio too long (max 500 characters)")
        user.bio = bio

    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "message": "Profile updated successfully",
        "location": user.location,
        "bio": user.bio
    }


@router.post("/profile/picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Upload a profile picture.

    Accepts: PNG, JPEG, GIF, WebP
    Max size: 5MB
    Automatically resized to 400x400 max

    Requires authentication.

    Args:
        file: Uploaded image file
        user: Current authenticated user

    Returns:
        Success message with new picture URL

    Raises:
        400: Invalid file type, too large, or corrupt image
        500: Failed to save image
    """
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Delete old profile picture if exists
    if user.profile_picture:
        delete_profile_picture(user.profile_picture)

    # Save new profile picture
    filename = save_profile_picture(content, file.filename, user.id)

    if not filename:
        raise HTTPException(status_code=500, detail="Failed to save profile picture")

    # Update user record
    user.profile_picture = filename
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "message": "Profile picture uploaded successfully",
        "profile_picture_url": get_profile_picture_url(filename)
    }


@router.delete("/profile/picture")
def delete_profile_picture_endpoint(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Delete your profile picture.

    Requires authentication.

    Args:
        user: Current authenticated user

    Returns:
        Success message

    Raises:
        404: User has no profile picture
    """
    if not user.profile_picture:
        raise HTTPException(status_code=404, detail="No profile picture to delete")

    # Delete file from storage
    filename = user.profile_picture
    delete_profile_picture(filename)

    # Update user record
    user.profile_picture = None
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()

    return {"message": "Profile picture deleted successfully"}


@router.get("/profile_pictures/{filename}")
async def serve_profile_picture(filename: str):
    """
    Serve a profile picture file.

    Tries NAS first (not implemented in this endpoint as NAS files
    would be served separately), falls back to local storage.

    Args:
        filename: Profile picture filename

    Returns:
        FileResponse with image

    Raises:
        404: File not found
    """
    # Check local storage
    local_path = LOCAL_STORAGE_PATH / "profile_pictures" / filename

    if local_path.exists() and local_path.is_file():
        return FileResponse(
            local_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=604800"}  # Cache for 1 week
        )

    # TODO: Implement NAS file serving if needed
    # For now, NAS files should be served via separate static file server or CDN

    raise HTTPException(status_code=404, detail="Profile picture not found")


@router.get("/profile/{username}/comments")
def get_user_comments(
    username: str,
    session: Session = Depends(get_session),
    limit: int = 50,
    offset: int = 0
):
    """
    Get a user's public comments.

    Returns recent comments by the user (excluding removed/hidden).

    Args:
        username: Username to get comments for
        limit: Maximum number of comments to return (default 50)
        offset: Offset for pagination (default 0)

    Returns:
        List of comments with URL and content

    Raises:
        404: User not found
    """
    # Get user
    user = session.exec(
        select(User).where(User.username == username)
    ).first()

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's comments
    statement = (
        select(Comment)
        .where(Comment.user_id == user.id)
        .where(Comment.is_removed == False)
        .where(Comment.is_hidden == False)
        .order_by(Comment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    comments = session.exec(statement).all()

    return {
        "username": username,
        "comments": [
            {
                "id": comment.id,
                "url": comment.url,
                "content": comment.content,
                "created_at": comment.created_at,
                "edited_at": comment.edited_at
            }
            for comment in comments
        ]
    }
