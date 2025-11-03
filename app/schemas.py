from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
import re

class UserCreate(BaseModel):
    username: str
    firstname: str
    lastname: str
    date_of_birth: Optional[datetime] = None
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """
        Validate password strength:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserRead(BaseModel):
    id: int
    username: str
    firstname: str
    lastname: str
    date_of_birth: Optional[datetime] = None
    email: EmailStr
    status: str
    type: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class UserLogin(BaseModel):
    username: str
    password: str

class LikeCreate(BaseModel):
    url: str

class CommentCreate(BaseModel):
    url: str
    content: str

class CommentRead(BaseModel):
    id: int
    url: str
    content: str
    created_at: datetime
    edited_at: Optional[datetime] = None
    user_id: int

class CommentWithUser(BaseModel):
    id: int
    url: str
    content: str
    created_at: datetime
    edited_at: Optional[datetime] = None
    user_id: int
    username: str
    profile_picture: Optional[str] = None  # Profile picture filename
    like_count: int = 0  # Number of likes on this comment
    user_has_liked: bool = False  # Whether current user has liked this comment

class CommentUpdate(BaseModel):
    content: str

class CommentLikeUser(BaseModel):
    """User information for displaying who liked a comment"""
    user_id: int
    username: str
    profile_picture: Optional[str] = None

class CommentLikers(BaseModel):
    """List of users who liked a comment (for displaying profile pictures)"""
    comment_id: int
    like_count: int
    likers: list[CommentLikeUser]  # Up to 10 users for display

class CommentVersionRead(BaseModel):
    id: int
    comment_id: int
    content: str
    edited_at: datetime

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    email: Optional[EmailStr] = None

class PasswordReset(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class AdminPasswordReset(BaseModel):
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class AccountStatusUpdate(BaseModel):
    status: str  # active or inactive

class PageViewCreate(BaseModel):
    url: str
    ip_address: str
    user_agent: Optional[str] = None

class PageViewStats(BaseModel):
    url: str
    view_count: int
    view_count_formatted: str
    unique_visitors: int
    last_viewed_at: Optional[datetime] = None

class PageViewTimelineDataPoint(BaseModel):
    date: str  # Date in YYYY-MM-DD format
    label: str  # Day name (M, T, W...) or month name (Jan, Feb...)
    count: int  # Number of views

class PageViewTimeline(BaseModel):
    url: str
    period: str  # 'weekly', 'monthly', or 'annual'
    data: list[PageViewTimelineDataPoint]
    total_views: int