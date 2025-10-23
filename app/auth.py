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
from slowapi import Limiter
from slowapi.util import get_remote_address
import os

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

templates = Jinja2Templates(directory="app/templates")

# Get environment for cookie security
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Template context helper
from datetime import datetime

def get_template_context(request, **kwargs):
    """Helper to add common template variables"""
    context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    context.update(kwargs)
    return context

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

def get_current_admin(current_user: User = Depends(get_current_user)):
    """Dependency to check if current user is an admin (type=1)"""
    if current_user.type != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Welcome, {current_user.username}!"}

@router.post("/api/register", response_model=UserRead, deprecated=True)
def register_api(user: UserCreate, session: Session = Depends(get_session)):
    """
    DEPRECATED: Use /accounts/register instead.
    This endpoint is maintained for backwards compatibility but lacks full audit logging.
    """
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check if email already exists
    existing_email = session.exec(select(User).where(User.email == user.email)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        firstname=user.firstname,
        lastname=user.lastname,
        date_of_birth=user.date_of_birth,
        email=user.email,
        hashed_password=hash_password(user.password),
        status="active",
        type=0
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@router.post("/api/login")
@limiter.limit("5/minute")
def login_api(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last_login timestamp for engagement tracking (issue #30)
    from datetime import datetime
    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    token = create_access_token({"sub": user.username})

    # Respond with token in JSON AND set in cookie
    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        secure=ENVIRONMENT == "production",  # Only send over HTTPS in production
        max_age=1800,
        samesite="lax"
    )
    return response

@router.get("/logout")
def logout(redirect: bool = True):
    """
    Logout the user by deleting the JWT cookie and username cookie.
    - If `?redirect=false`, returns JSON
    - Otherwise, redirects to login page
    """
    if redirect:
        response = RedirectResponse(url="/login", status_code=303)
    else:
        response = JSONResponse(content={"message": "Logged out successfully"})

    # Clear both cookies
    response.delete_cookie("access_token", domain=".kevsrobots.com" if ENVIRONMENT == "production" else None)
    response.delete_cookie("username", domain=".kevsrobots.com" if ENVIRONMENT == "production" else None)
    return response

@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    firstname: str = Form(...),
    lastname: str = Form(...),
    email: str = Form(...),
    date_of_birth: Optional[str] = Form(None),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    from .models import User
    from .utils import hash_password
    from datetime import datetime

    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username taken"})

    existing_email = session.exec(select(User).where(User.email == email)).first()
    if existing_email:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})

    # Parse date of birth if provided
    dob = None
    if date_of_birth:
        try:
            dob = datetime.strptime(date_of_birth, "%Y-%m-%d")
        except ValueError:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Invalid date format"})

    user = User(
        username=username,
        firstname=firstname,
        lastname=lastname,
        date_of_birth=dob,
        email=email,
        hashed_password=hash_password(password),
        status="active",
        type=0
    )
    session.add(user)
    session.commit()
    return RedirectResponse("/login", status_code=303)

@router.get("/login")
def login_page(request: Request, return_to: str = None):
    context = get_template_context(request, return_to=return_to)
    return templates.TemplateResponse("login.html", context)


@router.post("/login")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    return_to: str = Form(None),
    session: Session = Depends(get_session)
):
    from .models import User
    from .utils import verify_password, create_access_token

    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        context = get_template_context(request, error="Invalid credentials", return_to=return_to)
        return templates.TemplateResponse("login.html", context)

    token = create_access_token({"sub": user.username})

    # Check if user needs to reset password
    if user.force_password_reset:
        # Set temporary session cookie and redirect to password reset
        response = RedirectResponse(url="/force-password-reset", status_code=303)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=ENVIRONMENT == "production",
            samesite="lax",
            domain=".kevsrobots.com" if ENVIRONMENT == "production" else None
        )
        return response

    # Redirect to return_to URL if provided, otherwise go to account page
    redirect_url = return_to if return_to else "/account"
    response = RedirectResponse(url=redirect_url, status_code=303)

    # Set secure httponly token cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        secure=ENVIRONMENT == "production",
        samesite="lax",
        domain=".kevsrobots.com" if ENVIRONMENT == "production" else None
    )

    # Set username cookie (accessible to JavaScript for display purposes only)
    response.set_cookie(
        key="username",
        value=user.username,
        httponly=False,  # JavaScript can read this
        secure=ENVIRONMENT == "production",
        samesite="lax",
        domain=".kevsrobots.com" if ENVIRONMENT == "production" else None
    )

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

    # Check if email is already in use by another user
    existing_email = session.exec(select(User).where(User.email == email)).first()
    if existing_email and existing_email.id != user.id:
        like_count = session.exec(select(func.count()).where(Like.user_id == user.id)).one()
        comments = session.exec(select(Comment).where(Comment.user_id == user.id)).all()
        return templates.TemplateResponse("account.html", {
            "request": request,
            "user": user,
            "like_count": like_count,
            "comments": comments,
            "update_error": "Email already in use by another account"
        })

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
        "update_success": "Email updated successfully"
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

    response = RedirectResponse(url="/register", status_code=303)
    response.delete_cookie("access_token")
    return response

@router.get("/me")
def get_current_user_info(user: User = Depends(get_current_user)):
    return {"username": user.username}

# ============================================
# Admin Routes
# ============================================

@router.get("/admin")
def admin_page(
    request: Request,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin)
):
    """Admin dashboard - list all users"""
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    context = get_template_context(request, users=users, current_admin=admin)
    return templates.TemplateResponse("admin.html", context)

@router.post("/admin/force-password-reset/{user_id}")
def force_password_reset(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin)
):
    """Force a user to reset their password on next login"""
    user = session.exec(select(User).where(User.id == user_id)).first()

    if not user:
        users = session.exec(select(User).order_by(User.created_at.desc())).all()
        context = get_template_context(request, users=users, current_admin=admin, error="User not found")
        return templates.TemplateResponse("admin.html", context)

    # Don't allow forcing password reset on yourself
    if user.id == admin.id:
        users = session.exec(select(User).order_by(User.created_at.desc())).all()
        context = get_template_context(request, users=users, current_admin=admin, error="Cannot force password reset on yourself")
        return templates.TemplateResponse("admin.html", context)

    user.force_password_reset = True
    session.add(user)
    session.commit()

    # Redirect back to admin page with success message
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    context = get_template_context(request, users=users, current_admin=admin, success=f"Password reset required for {user.username}")
    return templates.TemplateResponse("admin.html", context)

@router.get("/force-password-reset")
def force_password_reset_page(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Display password reset page"""
    context = get_template_context(request)
    return templates.TemplateResponse("force_password_reset.html", context)

@router.post("/force-password-reset")
def handle_force_password_reset(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Handle forced password reset submission"""
    from .utils import hash_password

    # Validate passwords match
    if new_password != confirm_password:
        context = get_template_context(request, error="Passwords do not match")
        return templates.TemplateResponse("force_password_reset.html", context)

    # Validate password length
    if len(new_password) < 8:
        context = get_template_context(request, error="Password must be at least 8 characters long")
        return templates.TemplateResponse("force_password_reset.html", context)

    # Update password and clear force_password_reset flag
    user.hashed_password = hash_password(new_password)
    user.force_password_reset = False
    session.add(user)
    session.commit()

    # Redirect to account page with success message
    return RedirectResponse(url="/account", status_code=303)

@router.post("/admin/generate-reset-code/{user_id}")
def generate_reset_code(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin)
):
    """Generate a one-time password reset code for a user"""
    import secrets
    import string
    from datetime import timedelta

    user = session.exec(select(User).where(User.id == user_id)).first()

    if not user:
        users = session.exec(select(User).order_by(User.created_at.desc())).all()
        context = get_template_context(request, users=users, current_admin=admin, error="User not found")
        return templates.TemplateResponse("admin.html", context)

    # Generate a 8-character alphanumeric code
    alphabet = string.ascii_uppercase + string.digits
    reset_code = ''.join(secrets.choice(alphabet) for _ in range(8))

    # Set expiration to 24 hours from now
    from datetime import datetime
    expires_at = datetime.utcnow() + timedelta(hours=24)

    # Save code and expiration to user
    user.password_reset_code = reset_code
    user.code_expires_at = expires_at
    session.add(user)
    session.commit()

    # Return success with the code displayed
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    context = get_template_context(
        request,
        users=users,
        current_admin=admin,
        reset_code=reset_code,
        reset_code_user=user.username,
        success=f"Reset code generated for {user.username}"
    )
    return templates.TemplateResponse("admin.html", context)

@router.get("/reset-password")
def reset_password_page(request: Request):
    """Display password reset page"""
    context = get_template_context(request)
    return templates.TemplateResponse("reset_password.html", context)

@router.post("/reset-password")
def handle_reset_password(
    request: Request,
    username: str = Form(...),
    reset_code: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_session)
):
    """Handle password reset with code"""
    from .utils import hash_password
    from datetime import datetime

    # Validate passwords match
    if new_password != confirm_password:
        context = get_template_context(request, error="Passwords do not match", username=username)
        return templates.TemplateResponse("reset_password.html", context)

    # Validate password length
    if len(new_password) < 8:
        context = get_template_context(request, error="Password must be at least 8 characters long", username=username)
        return templates.TemplateResponse("reset_password.html", context)

    # Find user by username
    user = session.exec(select(User).where(User.username == username)).first()

    if not user:
        context = get_template_context(request, error="Invalid username or reset code", username=username)
        return templates.TemplateResponse("reset_password.html", context)

    # Check if user has a reset code
    if not user.password_reset_code:
        context = get_template_context(request, error="No reset code has been generated for this account", username=username)
        return templates.TemplateResponse("reset_password.html", context)

    # Check if code matches (case-insensitive)
    if user.password_reset_code.upper() != reset_code.upper():
        context = get_template_context(request, error="Invalid reset code", username=username)
        return templates.TemplateResponse("reset_password.html", context)

    # Check if code has expired
    if user.code_expires_at and user.code_expires_at < datetime.utcnow():
        context = get_template_context(request, error="Reset code has expired. Please request a new one from an administrator.", username=username)
        return templates.TemplateResponse("reset_password.html", context)

    # Update password and clear reset code
    user.hashed_password = hash_password(new_password)
    user.password_reset_code = None
    user.code_expires_at = None
    session.add(user)
    session.commit()

    # Redirect to login with success message
    return RedirectResponse(url="/login?reset=success", status_code=303)
