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
    type: int = Field(default=0)  # admin, regular user etc
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None  # Track last login time for engagement metrics

    # Optional relationships
    likes: List["Like"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    comments: List["Comment"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    account_logs: List["AccountLog"] = Relationship(back_populates="user", sa_relationship_kwargs={"foreign_keys": "[AccountLog.user_id]", "cascade": "all, delete-orphan"})
    changed_logs: List["AccountLog"] = Relationship(back_populates="changed_by_user", sa_relationship_kwargs={"foreign_keys": "[AccountLog.changed_by]"})

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