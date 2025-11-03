from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from .models import Like, Comment, CommentVersion
from .schemas import LikeCreate, CommentCreate, CommentRead, CommentWithUser, CommentUpdate, CommentVersionRead
from .database import get_session
from .auth import get_current_user, get_optional_user
from .models import User
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime

router = APIRouter()

@router.options("/like")
def like_options():
    """Handle preflight OPTIONS request for like"""
    return {}

@router.post("/like")
def toggle_like(
    like: LikeCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # Strip leading slash from URL to normalize storage
    url = like.url.lstrip('/')

    existing_like = session.exec(
        select(Like).where(Like.user_id == user.id, Like.url == url)
    ).first()

    if existing_like:
        session.delete(existing_like)
        session.commit()
        # Get updated like count after removal
        like_count = session.exec(select(func.count(Like.id)).where(Like.url == url)).one()
        return {"message": "Like removed", "liked": False, "like_count": like_count}

    # Strip leading slash from URL to normalize storage
    url = like.url.lstrip('/')
    new_like = Like(url=url, user_id=user.id)
    session.add(new_like)
    session.commit()
    # Get updated like count after addition
    like_count = session.exec(select(func.count(Like.id)).where(Like.url == url)).one()
    return {"message": "Like added", "liked": True, "like_count": like_count}

@router.options("/comment")
def comment_options():
    """Handle preflight OPTIONS request for comment"""
    return {}

@router.post("/comment", response_model=CommentRead)
def comment_url(comment: CommentCreate, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from .moderation import validate_comment_content, sanitize_content

    # Sanitize content
    sanitized_content = sanitize_content(comment.content)

    # Validate content
    is_valid, error_message = validate_comment_content(sanitized_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # Strip leading slash from URL to normalize storage
    url = comment.url.lstrip('/')
    new_comment = Comment(url=url, content=sanitized_content, user_id=user.id)
    session.add(new_comment)
    session.commit()
    session.refresh(new_comment)
    return new_comment

@router.get("/test-versions")
def test_versions():
    return {"message": "Test endpoint works", "timestamp": datetime.utcnow().isoformat()}

@router.get("/comments/{comment_id:int}/versions")
def get_comment_versions(
    comment_id: int,
    session: Session = Depends(get_session)
):
    """
    Get version history for a comment.
    Returns all previous versions sorted by edited_at (newest first).
    """
    print(f"GET VERSIONS ENDPOINT CALLED with comment_id={comment_id}")

    # Check if comment exists
    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Get all versions
    versions = session.exec(
        select(CommentVersion)
        .where(CommentVersion.comment_id == comment_id)
        .order_by(CommentVersion.edited_at.desc())
    ).all()

    print(f"Found {len(versions)} versions")

    # Return as list of dicts
    result = []
    for v in versions:
        result.append({
            "id": v.id,
            "comment_id": v.comment_id,
            "content": v.content,
            "edited_at": v.edited_at.isoformat() if v.edited_at else None
        })

    return result

@router.get("/comments/{url:path}", response_model=List[CommentWithUser])
def get_comments_with_usernames(url: str, session: Session = Depends(get_session)):
    # Strip leading slash from URL to normalize storage
    url = url.lstrip('/')

    statement = (
        select(Comment, User)
        .where(Comment.url == url)
        .where(Comment.user_id == User.id)
        .where(Comment.is_hidden == False)  # Only show non-hidden comments
        .where(Comment.is_removed == False)  # Exclude removed comments
        .order_by(Comment.created_at.desc())
    )
    results = session.exec(statement).all()

    comments = [
        CommentWithUser(
            id=comment.id,
            url=comment.url,
            content=comment.content,
            created_at=comment.created_at,
            edited_at=comment.edited_at,
            user_id=user.id,
            username=user.username,
            profile_picture=user.profile_picture,
        )
        for comment, user in results
    ]
    return comments

@router.options("/comments/{comment_id}")
def comment_id_options(comment_id: int):
    """Handle preflight OPTIONS request for comment edit/delete"""
    return {}

@router.put("/comments/{comment_id}", response_model=CommentRead)
def edit_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Edit a comment - only the original author can edit their comment.
    Creates a version history entry with the previous content.
    """
    from .moderation import validate_comment_content, sanitize_content

    # Get the comment
    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check if user is the author
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the original author can edit this comment")

    # Sanitize and validate new content
    sanitized_content = sanitize_content(comment_update.content)
    is_valid, error_message = validate_comment_content(sanitized_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # Save current version to history before updating
    version = CommentVersion(
        comment_id=comment.id,
        content=comment.content,
        edited_at=comment.edited_at or comment.created_at  # Use edited_at if exists, else created_at
    )
    session.add(version)

    # Update comment
    comment.content = sanitized_content
    comment.edited_at = datetime.utcnow()

    session.add(comment)
    session.commit()
    session.refresh(comment)

    return comment

@router.delete("/comments/{comment_id}")
def remove_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Soft-delete a comment - only the original author can remove their comment.
    The comment remains in the database but is marked as removed.
    """
    # Get the comment
    comment = session.exec(select(Comment).where(Comment.id == comment_id)).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check if user is the author
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the original author can remove this comment")

    # Check if already removed
    if comment.is_removed:
        raise HTTPException(status_code=400, detail="Comment already removed")

    # Mark as removed (soft delete)
    comment.is_removed = True
    comment.removed_at = datetime.utcnow()

    session.add(comment)
    session.commit()

    return {"message": "Comment removed successfully"}

@router.get("/likes/{url:path}")
def count_likes(
    url: str,
    session: Session = Depends(get_session)
):
    """
    Get like count for a URL.
    Available to all users (logged in or not).
    To check if a specific user has liked, use POST /interact/like with check_only=true
    """
    # Strip leading slash from URL to normalize storage
    url = url.lstrip('/')

    # Get total like count
    like_count = session.exec(select(func.count()).where(Like.url == url)).one()

    return {
        "url": url,
        "like_count": like_count
    }


@router.options("/like-status/{url:path}")
def like_status_options(url: str):
    """Handle preflight OPTIONS request for like status"""
    return {}


@router.get("/like-status/{url:path}")
def get_combined_like_status(
    url: str,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user)
):
    """
    Get like count and user like status in a single call.
    If user is not authenticated, only returns like count.
    This reduces 2 API calls to 1 on page load.
    Works for both authenticated and anonymous users.
    """
    # Strip leading slash from URL to normalize storage
    url = url.lstrip('/')

    # Get total like count
    like_count = session.exec(select(func.count()).where(Like.url == url)).one()

    # Check if user has liked (only if authenticated)
    user_has_liked = False
    if user:
        existing_like = session.exec(
            select(Like).where(Like.user_id == user.id, Like.url == url)
        ).first()
        user_has_liked = existing_like is not None

    return {
        "url": url,
        "like_count": like_count,
        "user_has_liked": user_has_liked
    }


@router.get("/user-like-status/{url:path}")
def get_user_like_status(
    url: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Check if the current user has liked a specific URL.
    DEPRECATED: Use /like-status/{url} instead for better performance.
    Returns the like_id if liked, null if not.
    Requires authentication.
    """
    # Strip leading slash from URL to normalize storage
    url = url.lstrip('/')

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