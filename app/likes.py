"""
Likes API endpoints
Handles like/unlike functionality for content URLs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from .models import User, Like
from .auth import get_current_user
from .database import get_session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/likes", tags=["likes"])


class LikeCreate(BaseModel):
    url: str


class LikeResponse(BaseModel):
    id: int
    url: str
    user_id: int
    created_at: datetime


class LikeCountResponse(BaseModel):
    url: str
    like_count: int
    user_has_liked: bool
    user_like_id: Optional[int] = None


class MostLikedResponse(BaseModel):
    url: str
    like_count: int
    last_liked_at: datetime


@router.post("", response_model=LikeResponse, status_code=status.HTTP_201_CREATED)
def create_like(
    like_data: LikeCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Like a piece of content.
    User must be authenticated.
    Can only like the same URL once.
    """
    # Check if user has already liked this URL
    existing_like = session.exec(
        select(Like).where(
            Like.url == like_data.url,
            Like.user_id == current_user.id
        )
    ).first()

    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already liked this content"
        )

    # Create new like
    new_like = Like(
        url=like_data.url,
        user_id=current_user.id
    )
    session.add(new_like)
    session.commit()
    session.refresh(new_like)

    return new_like


@router.delete("/{like_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_like(
    like_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Unlike a piece of content (delete a like).
    User must be authenticated and can only delete their own likes.
    """
    like = session.exec(select(Like).where(Like.id == like_id)).first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )

    # Ensure user can only delete their own likes
    if like.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only unlike your own likes"
        )

    session.delete(like)
    session.commit()

    return None


@router.get("/count", response_model=LikeCountResponse)
def get_like_count(
    url: str,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get the like count for a URL and whether the current user has liked it.
    Available to all users (logged in or not).
    """
    # Get total like count
    like_count = session.exec(
        select(func.count()).where(Like.url == url)
    ).one()

    # Check if current user has liked this (if authenticated)
    user_has_liked = False
    user_like_id = None
    if current_user:
        user_like = session.exec(
            select(Like).where(
                Like.url == url,
                Like.user_id == current_user.id
            )
        ).first()
        if user_like:
            user_has_liked = True
            user_like_id = user_like.id

    return {
        "url": url,
        "like_count": like_count,
        "user_has_liked": user_has_liked,
        "user_like_id": user_like_id
    }


@router.get("/most-liked", response_model=list[MostLikedResponse])
def get_most_liked(
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get the most liked content.
    Returns a list of URLs sorted by like count (highest to lowest).
    Available to all users.
    """
    # Query the materialized view
    from sqlalchemy import text

    query = text("""
        SELECT url, like_count, last_liked_at
        FROM most_liked_content
        LIMIT :limit
    """)

    result = session.execute(query, {"limit": limit})

    return [
        {
            "url": row[0],
            "like_count": row[1],
            "last_liked_at": row[2]
        }
        for row in result
    ]


@router.post("/refresh-view", status_code=status.HTTP_200_OK)
def refresh_most_liked_view(session: Session = Depends(get_session)):
    """
    Refresh the materialized view for most liked content.
    This should be called periodically to keep the view up to date.
    Can be triggered manually or via a cron job.
    """
    from sqlalchemy import text

    # Refresh the materialized view concurrently (allows reads during refresh)
    session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY most_liked_content"))
    session.commit()

    return {"message": "Most liked content view refreshed successfully"}
