""" FastAPI application for user authentication, comments, and likes."""

from typing import List

from auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from database import get_session, init_db
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import Comment, Like, User
from schemas import CommentCreate, LikeCreate, Token, UserCreate
from sqlmodel import Session, select

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
init_db()

# Auth Helpers
def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    """ Get the current user from the token """

    username = decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Register
@app.post("/register", response_model=Token)
def register(user_data: UserCreate, session: Session = Depends(get_session)):
    """ Register a new user """

    if session.exec(select(User).where(User.username == user_data.username)).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=user_data.username, hashed_password=get_password_hash(user_data.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# Login
@app.post("/loginapi", response_model=Token)
def loginapi(form_data: OAuth2PasswordRequestForm = Depends(), 
          session: Session = Depends(get_session)) -> dict[str,str]:
    """ Check if user exists and verify password """

    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# Post a comment
@app.post("/comment")
def post_comment(comment: CommentCreate, 
                 user: User = Depends(get_current_user), 
                 session: Session = Depends(get_session)) -> dict[str,str]:
    """ Post a user comment to url """    
    new_comment = Comment(url=comment.url, content=comment.content, user_id=user.id)
    session.add(new_comment)
    session.commit()
    return {"message": "Comment added"}

# Post a like
@app.post("/like")
def like_url(like: LikeCreate, user: 
             User = Depends(get_current_user), 
             session: Session = Depends(get_session)) -> dict[str,str]:
    """ Post a user like to url """

    # Check if the user has already liked the URL
    existing = session.exec(select(Like).where(Like.url == like.url, Like.user_id == user.id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already liked")
    new_like = Like(url=like.url, user_id=user.id)
    session.add(new_like)
    session.commit()
    return {"message": "Like added"}

# Get comments for a URL
@app.get("/comments/{url}", response_model=List[str])
def get_comments(url: str, session: Session = Depends(get_session)) -> List[str]:
    """ Get all comments for a URL """

    comments = session.exec(select(Comment).where(Comment.url == url)).all()
    return [f"{c.user.username}: {c.content}" for c in comments]

# Get likes count for a URL
@app.get("/likes/{url}")
def get_likes(url: str, session: Session = Depends(get_session)) -> dict[str,int]:
    """ Get the number of likes for a URL """

    count = session.exec(select(Like).where(Like.url == url)).count()
    return {"url": url, "likes": count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/login")
def login():
    """ Login page """

    return Title(
                 Form(action="/loginapi", method="post", 
                      Input(name="username", label="Username"),
                      Input(name="password", label="Password", type="password"),
                      Button(type="submit", text="Login")))




    