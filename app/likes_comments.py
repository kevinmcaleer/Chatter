from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from .models import Like, Comment
from .schemas import LikeCreate, CommentCreate, CommentRead, CommentWithUser
from .database import get_session
from .auth import get_current_user
from .models import User
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime

router = APIRouter()

@router.post("/like")
def toggle_like(
    like: LikeCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    existing_like = session.exec(
        select(Like).where(Like.user_id == user.id, Like.url == like.url)
    ).first()

    if existing_like:
        session.delete(existing_like)
        session.commit()
        return {"message": "Like removed", "liked": False}

    new_like = Like(url=like.url, user_id=user.id)
    session.add(new_like)
    session.commit()
    return {"message": "Like added", "liked": True}


@router.post("/comment", response_model=CommentRead)
def comment_url(comment: CommentCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from .moderation import validate_comment_content, sanitize_content

    # Sanitize content
    sanitized_content = sanitize_content(comment.content)

    # Validate content
    is_valid, error_message = validate_comment_content(sanitized_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    new_comment = Comment(url=comment.url, content=sanitized_content, user_id=user.id)
    session.add(new_comment)
    session.commit()
    session.refresh(new_comment)
    return new_comment

@router.get("/comments/{url}", response_model=List[CommentWithUser])
def get_comments_with_usernames(url: str, session: Session = Depends(get_session)):
    statement = (
        select(Comment, User)
        .where(Comment.url == url)
        .where(Comment.user_id == User.id)
        .where(Comment.is_hidden == False)  # Only show non-hidden comments
        .order_by(Comment.created_at.desc())
    )
    results = session.exec(statement).all()

    comments = [
        CommentWithUser(
            id=comment.id,
            url=comment.url,
            content=comment.content,
            created_at=comment.created_at,
            user_id=user.id,
            username=user.username,
        )
        for comment, user in results
    ]
    return comments

@router.get("/likes/{url}")
def count_likes(
    url: str,
    session: Session = Depends(get_session)
):
    """
    Get like count for a URL.
    Available to all users (logged in or not).
    To check if a specific user has liked, use POST /interact/like with check_only=true
    """
    # Get total like count
    like_count = session.exec(select(func.count()).where(Like.url == url)).one()

    return {
        "url": url,
        "like_count": like_count
    }


@router.get("/user-like-status/{url}")
def get_user_like_status(
    url: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Check if the current user has liked a specific URL.
    Returns the like_id if liked, null if not.
    Requires authentication.
    """
    user_like = session.exec(
        select(Like).where(Like.url == url, Like.user_id == user.id)
    ).first()

    return {
        "url": url,
        "user_has_liked": user_like is not None,
        "like_id": user_like.id if user_like else None
    }


@router.get("/most-liked")
def get_most_liked(limit: int = 10, session: Session = Depends(get_session)):
    """
    Get the most liked content from the materialized view.
    Returns URLs sorted by like count (highest to lowest).
    """
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
            "last_liked_at": row[2].isoformat() if row[2] else None
        }
        for row in result
    ]


@router.post("/refresh-most-liked")
def refresh_most_liked_view(session: Session = Depends(get_session)):
    """
    Refresh the materialized view for most liked content.
    Should be called periodically to keep the view up to date.
    """
    from sqlalchemy import text

    try:
        session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY most_liked_content"))
        session.commit()
        return {"message": "Most liked content view refreshed successfully"}
    except Exception as e:
        return {"message": f"Error refreshing view: {str(e)}", "status": "error"}


# ============================================
# Comment Moderation Endpoints
# ============================================

from pydantic import BaseModel

class ReportCommentRequest(BaseModel):
    reason: str  # spam, abusive, inappropriate, other
    details: Optional[str] = None

@router.post("/comments/{comment_id}/report")
def report_comment(
    comment_id: int,
    report_data: ReportCommentRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Report a comment as spam, abusive, or inappropriate.
    Requires authentication.
    """
    import json

    # Get the comment
    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Increment flag count
    comment.flag_count += 1
    comment.is_flagged = True

    # Add reason to flag_reasons (stored as JSON)
    existing_reasons = []
    if comment.flag_reasons:
        try:
            existing_reasons = json.loads(comment.flag_reasons)
        except:
            existing_reasons = []

    existing_reasons.append({
        "reported_by": user.id,
        "reason": report_data.reason,
        "details": report_data.details,
        "reported_at": datetime.utcnow().isoformat()
    })

    comment.flag_reasons = json.dumps(existing_reasons)

    session.add(comment)
    session.commit()

    return {
        "message": "Comment reported successfully",
        "flag_count": comment.flag_count
    }


@router.get("/comments/flagged")
def get_flagged_comments(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_user)
):
    """
    Get all flagged comments (admin only).
    Returns comments that have been reported by users.
    """
    from .auth import get_current_admin

    # Check if user is admin
    if admin.type != 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    statement = (
        select(Comment, User)
        .where(Comment.is_flagged == True)
        .where(Comment.user_id == User.id)
        .order_by(Comment.flag_count.desc(), Comment.created_at.desc())
    )
    results = session.exec(statement).all()

    import json
    flagged_comments = []
    for comment, user in results:
        flag_reasons = []
        if comment.flag_reasons:
            try:
                flag_reasons = json.loads(comment.flag_reasons)
            except:
                pass

        flagged_comments.append({
            "id": comment.id,
            "url": comment.url,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "user_id": user.id,
            "username": user.username,
            "flag_count": comment.flag_count,
            "flag_reasons": flag_reasons,
            "is_hidden": comment.is_hidden,
            "reviewed_at": comment.reviewed_at.isoformat() if comment.reviewed_at else None
        })

    return flagged_comments


@router.post("/comments/{comment_id}/hide")
def hide_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_user)
):
    """
    Hide a comment (admin only).
    Hidden comments will not be displayed to users.
    """
    # Check if user is admin
    if admin.type != 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.is_hidden = True
    comment.reviewed_at = datetime.utcnow()
    comment.reviewed_by = admin.id

    session.add(comment)
    session.commit()

    return {"message": "Comment hidden successfully"}


@router.post("/comments/{comment_id}/unhide")
def unhide_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_user)
):
    """
    Unhide a comment (admin only).
    """
    # Check if user is admin
    if admin.type != 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.is_hidden = False
    comment.reviewed_at = datetime.utcnow()
    comment.reviewed_by = admin.id

    session.add(comment)
    session.commit()

    return {"message": "Comment unhidden successfully"}


@router.post("/comments/{comment_id}/clear-flags")
def clear_comment_flags(
    comment_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_user)
):
    """
    Clear flags on a comment (admin only).
    Marks the comment as reviewed and removes flagged status.
    """
    # Check if user is admin
    if admin.type != 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.is_flagged = False
    comment.reviewed_at = datetime.utcnow()
    comment.reviewed_by = admin.id

    session.add(comment)
    session.commit()

    return {"message": "Comment flags cleared successfully"}