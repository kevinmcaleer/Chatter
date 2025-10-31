from sqlmodel import SQLModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .models import User

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    firstname: str
    lastname: str
    date_of_birth: Optional[datetime] = None
    email: str = Field(index=True, unique=True)
    status: str = Field(default="active")  # active or inactive
    hashed_password: str
    type: int = Field(default=0)  # 0=regular user, 1=admin
    force_password_reset: bool = Field(default=False)  # Force user to reset password on next login
    password_reset_code: Optional[str] = None  # One-time code for password reset
    code_expires_at: Optional[datetime] = None  # Expiration time for reset code
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None  # Track last login time for engagement metrics

    # Profile fields (Issue #44)
    profile_picture: Optional[str] = None  # Filename of profile picture stored on NAS
    location: Optional[str] = None  # Country/location string for timezone/localization
    bio: Optional[str] = None  # Short biography/about me text

    # Optional relationships
    likes: List["Like"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    comments: List["Comment"] = Relationship(back_populates="user", sa_relationship_kwargs={"foreign_keys": "[Comment.user_id]", "cascade": "all, delete-orphan"})
    reviewed_comments: List["Comment"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Comment.reviewed_by]"})
    account_logs: List["AccountLog"] = Relationship(back_populates="user", sa_relationship_kwargs={"foreign_keys": "[AccountLog.user_id]", "cascade": "all, delete-orphan"})
    changed_logs: List["AccountLog"] = Relationship(back_populates="changed_by_user", sa_relationship_kwargs={"foreign_keys": "[AccountLog.changed_by]"})

class Like(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)  # Index for fast lookups by URL
    user_id: int = Field(foreign_key="user.id", index=True)  # Index for fast lookups by user
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Track when like was created

    user: Optional["User"] = Relationship(back_populates="likes")

    class Config:
        # Add unique constraint to prevent duplicate likes
        # User can only like the same URL once
        unique_together = [("url", "user_id")]

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)  # Index for fast lookups by URL
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None  # Track when comment was last edited
    user_id: int = Field(foreign_key="user.id", index=True)  # Index for fast lookups by user

    # Moderation fields
    is_flagged: bool = Field(default=False)  # Whether comment has been flagged for review
    flag_count: int = Field(default=0)  # Number of times comment has been reported
    flag_reasons: Optional[str] = None  # JSON string of report reasons
    is_hidden: bool = Field(default=False)  # Admin can hide abusive comments
    reviewed_at: Optional[datetime] = None  # When admin reviewed the flagged comment
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id")  # Admin who reviewed

    # Soft delete fields
    is_removed: bool = Field(default=False)  # User can soft-delete their own comments
    removed_at: Optional[datetime] = None  # When comment was removed by author

    user: Optional["User"] = Relationship(back_populates="comments", sa_relationship_kwargs={"foreign_keys": "[Comment.user_id]"})
    reviewer: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Comment.reviewed_by]", "overlaps": "reviewed_comments"})
    versions: List["CommentVersion"] = Relationship(back_populates="comment", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class CommentVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    comment_id: int = Field(foreign_key="comment.id", index=True)
    content: str  # Previous version of the comment content
    edited_at: datetime = Field(default_factory=datetime.utcnow)  # When this version was created

    comment: Optional["Comment"] = Relationship(back_populates="versions")

class AccountLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    action: str  # created, updated, activated, deactivated, deleted
    field_changed: Optional[str] = None  # specific field that was changed
    old_value: Optional[str] = None  # previous value
    new_value: Optional[str] = None  # new value
    changed_by: Optional[int] = Field(default=None, foreign_key="user.id")  # user_id of who made the change
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Relationships
    user: Optional["User"] = Relationship(back_populates="account_logs", sa_relationship_kwargs={"foreign_keys": "[AccountLog.user_id]"})
    changed_by_user: Optional["User"] = Relationship(back_populates="changed_logs", sa_relationship_kwargs={"foreign_keys": "[AccountLog.changed_by]"})

class PageView(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)  # Index for fast lookups by URL
    ip_address: str = Field(index=True)  # Track IP for unique visitor counts
    viewed_at: datetime = Field(default_factory=datetime.utcnow, index=True)  # Track when page was viewed
    user_agent: Optional[str] = None  # Track browser/device information