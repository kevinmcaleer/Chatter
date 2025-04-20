"""
Models for the application using SQLModel.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str

    likes: List["Like"] = Relationship(back_populates="user")
    comments: List["Comment"] = Relationship(back_populates="user")


class Like(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    user_id: int = Field(foreign_key="user.id")

    user: Optional[User] = Relationship(back_populates="likes")


class Comment(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: int = Field(foreign_key="user.id")

    user: Optional[User] = Relationship(back_populates="comments")
