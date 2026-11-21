"""Social endpoints for project cards and public profiles on kevsrobots.

* ``POST /interact/like-status/batch`` - like counts (and the caller's own
  likes) for a whole grid of cards in one request.
* ``GET  /interact/users/{username}/liked`` - the URLs someone has liked,
  only when they chose to show them (or when they ask for their own).
* ``PUT  /interact/me/privacy`` - turn that choice on or off.

The choice lives in its own ``user_privacy`` table rather than on ``users``
so a new image can start before migration 021 is run: startup's
``create_all`` makes the table, and nothing that reads ``users`` changes.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select

from .auth import get_current_user, get_optional_user
from .database import get_session
from .models import Comment, Like, User, UserPrivacy

router = APIRouter()

MAX_BATCH = 50


class LikeStatusBatchRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=MAX_BATCH)


class LikeStatus(BaseModel):
    like_count: int
    user_has_liked: bool
    comment_count: int = 0


class LikeStatusBatchResponse(BaseModel):
    items: dict[str, LikeStatus]


class LikedResponse(BaseModel):
    username: str
    urls: list[str]
    limit: int
    offset: int


class PrivacyUpdate(BaseModel):
    likes_public: bool


class PrivacyResponse(BaseModel):
    likes_public: bool


def _key(url: str) -> str:
    """Likes are stored without a leading slash."""
    return url.lstrip("/")


def _like_counts(session: Session, keys: list[str]) -> dict[str, int]:
    rows = session.exec(
        select(Like.url, func.count(Like.id)).where(Like.url.in_(keys)).group_by(Like.url)
    ).all()
    return {url: int(count) for url, count in rows}


def _comment_counts(session: Session, keys: list[str]) -> dict[str, int]:
    """Visible comments (not hidden or removed), replies included."""
    rows = session.exec(
        select(Comment.url, func.count(Comment.id))
        .where(Comment.url.in_(keys), Comment.is_hidden == False, Comment.is_removed == False)  # noqa: E712
        .group_by(Comment.url)
    ).all()
    return {url: int(count) for url, count in rows}


def _liked_by(session: Session, user: Optional[User], keys: list[str]) -> set[str]:
    if user is None:
        return set()
    return set(session.exec(
        select(Like.url).where(Like.user_id == user.id, Like.url.in_(keys))
    ).all())


@router.post("/like-status/batch", response_model=LikeStatusBatchResponse)
def like_status_batch(
    body: LikeStatusBatchRequest,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Like count, "have I liked it" and comment count for up to 50 URLs.
    Answers are keyed by the URL exactly as sent. Anonymous callers get
    user_has_liked=false."""
    keys = list({_key(u) for u in body.urls})
    likes = _like_counts(session, keys)
    comments = _comment_counts(session, keys)
    mine = _liked_by(session, user, keys)
    return LikeStatusBatchResponse(items={
        url: LikeStatus(
            like_count=likes.get(_key(url), 0),
            user_has_liked=_key(url) in mine,
            comment_count=comments.get(_key(url), 0),
        )
        for url in body.urls
    })


def likes_are_public(session: Session, user_id: int) -> bool:
    row = session.get(UserPrivacy, user_id)
    return bool(row and row.likes_public)


@router.get("/users/{username}/liked", response_model=LikedResponse)
def list_liked(
    username: str,
    prefix: str = Query("", max_length=200, description="Only URLs starting with this, e.g. projects/"),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    viewer: Optional[User] = Depends(get_optional_user),
):
    """What ``username`` has liked, newest first. 404 for an unknown user;
    403 unless they made their likes public or are asking for their own."""
    owner = session.exec(select(User).where(User.username == username)).first()
    if owner is None or owner.status != "active":
        raise HTTPException(status_code=404, detail="User not found")
    is_self = viewer is not None and viewer.id == owner.id
    if not is_self and not likes_are_public(session, owner.id):
        raise HTTPException(status_code=403, detail="This person keeps their likes private")
    query = select(Like.url).where(Like.user_id == owner.id, Like.url.is_not(None))
    if prefix:
        query = query.where(Like.url.startswith(_key(prefix)))
    urls = session.exec(
        query.order_by(Like.created_at.desc(), Like.id.desc()).limit(limit).offset(offset)
    ).all()
    return LikedResponse(username=owner.username, urls=list(urls), limit=limit, offset=offset)


@router.get("/me/privacy", response_model=PrivacyResponse)
def get_privacy(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return PrivacyResponse(likes_public=likes_are_public(session, user.id))


@router.put("/me/privacy", response_model=PrivacyResponse)
def update_privacy(
    body: PrivacyUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Show or hide the Liked tab on your public profile."""
    row = session.get(UserPrivacy, user.id) or UserPrivacy(user_id=user.id)
    row.likes_public = body.likes_public
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    return PrivacyResponse(likes_public=row.likes_public)
