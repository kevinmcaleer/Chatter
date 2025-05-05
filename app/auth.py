from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from .models import User
from .schemas import UserCreate, UserRead, UserLogin
from .database import get_session
from .utils import hash_password, verify_password

router = APIRouter()

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@router.post("/login")
def login(user: UserLogin, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user_id": db_user.id}

@router.post("/logout")
def logout():
    # If you're using JWTs, this would be handled client-side by deleting the token.
    return {"message": "Logout successful"}
