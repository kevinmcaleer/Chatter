from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

class CommentCreate(BaseModel):
    url: str
    content: str

class LikeCreate(BaseModel):
    url: str
