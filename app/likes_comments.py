from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from .models import Like, Comment
from .schemas import LikeCreate, CommentCreate, CommentRead, CommentWithUser
from .database import get_session
from .auth import get_current_user
from .models import User
from typing import List
from sqlalchemy import func

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
    new_comment = Comment(url=comment.url, content=comment.content, user_id=user.id)
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
def count_likes(url: str, session: Session = Depends(get_session)):
    result = session.exec(select(func.count()).where(Like.url == url)).one()
    return {"url": url, "like_count": result}