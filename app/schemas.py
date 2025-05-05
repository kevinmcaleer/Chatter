from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr

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
    username: str
    email: EmailStr