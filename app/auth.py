from fastapi import APIRouter, Depends, HTTPException, status, Request   
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from .models import User, Like, Comment
from .schemas import UserCreate, UserRead, UserUpdate
from .database import get_session
from .utils import decode_access_token, create_access_token, hash_password, verify_password
from fastapi import Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.routing import APIRouter
from fastapi import Cookie, Form
from sqlalchemy import func
from pydantic import EmailStr, ValidationError, BaseModel
from fastapi import Header, Cookie
from typing import Optional

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class EmailCheckModel(BaseModel):
    email: EmailStr

def get_current_user(
    token_cookie: Optional[str] = Cookie(default=None, alias="access_token"),
    token_header: Optional[str] = Header(default=None, alias="Authorization"),
    session: Session = Depends(get_session)
):
    token = None

    # Use Bearer token from Authorization header if provided
    if token_header and token_header.startswith("Bearer "):
        token = token_header[7:]
    # Fallback to token from HttpOnly cookie
    elif token_cookie and token_cookie.startswith("Bearer "):
        token = token_cookie[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = session.exec(select(User).where(User.username == payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Welcome, {current_user.username}!"}

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
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username})

    # Respond with token in JSON AND set in cookie
    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=1800,
        samesite="lax"
    )
    return response

@router.get("/logout")
def logout(redirect: bool = True):
    """
    Logout the user by deleting the JWT cookie.
    - If `?redirect=false`, returns JSON
    - Otherwise, redirects to login page
    """
    if redirect:
        response = RedirectResponse(url="/auth/login-page", status_code=303)
    else:
        response = JSONResponse(content={"message": "Logged out successfully"})

    response.delete_cookie("access_token")
    return response

@router.get("/register-page")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register-page")
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    from .models import User
    from .utils import hash_password
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username taken"})

    user = User(username=username, email=email, hashed_password=hash_password(password))
    session.add(user)
    session.commit()
    return RedirectResponse("/auth/login-page", status_code=303)

@router.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login-page")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    from .models import User
    from .utils import verify_password, create_access_token

    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

    token = create_access_token({"sub": user.username})
    response = RedirectResponse(url="/auth/account", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response

@router.get("/account")
def account_page(request: Request, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    like_count = session.exec(select(func.count()).where(Like.user_id == user.id)).one()
    
    comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()

    return templates.TemplateResponse("account.html", {
        "request": request,
        "user" : user,
        "like_count": like_count,
        "comments": comments,
    })

@router.post("/account/update")
def update_account(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    from sqlalchemy import func

    # ✅ Email format check
    try:
        EmailCheckModel(email=email)
    except ValidationError:
        like_count = session.exec(select(func.count()).where(Like.user_id == user.id)).one()
        comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
        return templates.TemplateResponse("account.html", {
            "request": request,
            "user": user,
            "like_count": like_count,
            "comments": comments,
            "update_error": "Invalid email format"
        })

    # Username conflict check
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing and existing.id != user.id:
        like_count = session.exec(select(func.count()).where(Like.user_id == user.id)).one()
        comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
        return templates.TemplateResponse("account.html", {
            "request": request,
            "user": user,
            "like_count": like_count,
            "comments": comments,
            "update_error": "Username already taken"
        })

    user.username = username
    user.email = email
    session.add(user)
    session.commit()

    like_count = session.exec(select(func.count()).where(Like.user_id == user.id)).one()
    comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
    return templates.TemplateResponse("account.html", {
        "request": request,
        "user": user,
        "like_count": like_count,
        "comments": comments,
        "update_success": "Account updated successfully"
    })


@router.post("/account/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    from .utils import verify_password, hash_password

    if not verify_password(current_password, user.hashed_password):
        like_count = session.exec(select(Like).where(Like.user_id == user.id)).count()
        comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
        return templates.TemplateResponse("account.html", {
            "request": request,
            "like_count": like_count,
            "comments": comments,
            "password_error": "Incorrect current password"
        })

    user.hashed_password = hash_password(new_password)
    session.add(user)
    session.commit()

    like_count = session.exec(select(Like).where(Like.user_id == user.id)).count()
    comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
    return templates.TemplateResponse("account.html", {
        "request": request,
        "like_count": like_count,
        "comments": comments,
        "password_success": "Password updated successfully"
    })

@router.post("/account/delete")
def delete_account(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # delete related likes and comments first (to avoid FK constraint)
    
    likes = session.exec(select(Like).where(Like.user_id == user.id)).all()
    for like in likes:
        session.delete(like)

    comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
    for comment in comments:
        session.delete(comment)

    session.delete(user)
    session.commit()


    session.exec(select(Comment).where(Comment.user_id == user.id)).delete()
    session.delete(user)
    session.commit()

    response = RedirectResponse(url="/auth/register-page", status_code=303)
    response.delete_cookie("access_token")
    return response

@router.get("/me")
def get_current_user_info(user: User = Depends(get_current_user)):
    return {"username": user.username}
