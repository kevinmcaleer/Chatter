from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str
    firstname: str
    lastname: str
    date_of_birth: Optional[datetime] = None
    email: EmailStr
    password: str

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
    user_id: int

class CommentWithUser(BaseModel):
    id: int
    url: str
    content: str
    created_at: datetime
    user_id: int
    username: str

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    email: Optional[EmailStr] = None

class PasswordReset(BaseModel):
    old_password: str
    new_password: str

class AdminPasswordReset(BaseModel):
    new_password: str

class AccountStatusUpdate(BaseModel):
    status: str  # active or inactive