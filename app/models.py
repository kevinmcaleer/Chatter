from sqlmodel import SQLModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .models import User

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

    # Optional relationships
    likes: List["Like"] = Relationship(back_populates="user")
    comments: List["Comment"] = Relationship(back_populates="user")

class Like(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    user_id: int = Field(foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="likes")

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: int = Field(foreign_key="user.id")

    user: Optional["User"] = Relationship(back_populates="comments")