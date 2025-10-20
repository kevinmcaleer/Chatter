from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from .models import User, AccountLog
from .schemas import UserCreate, UserRead, UserUpdate, PasswordReset, AdminPasswordReset, AccountStatusUpdate
from .database import get_session
from .utils import hash_password, verify_password
from .auth import get_current_user
from datetime import datetime
from typing import Optional

router = APIRouter()

async def log_account_change(
    session: Session,
    user_id: int,
    action: str,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    changed_by: Optional[int] = None,
    request: Optional[Request] = None
):
    """Helper function to log account changes"""
    log = AccountLog(
        user_id=user_id,
        action=action,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    session.add(log)
    session.commit()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_account(
    user_data: UserCreate,
    request: Request,
    session: Session = Depends(get_session)
):
    """Register a new user account"""

    # Check if username already exists
    existing_user = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        firstname=user_data.firstname,
        lastname=user_data.lastname,
        date_of_birth=user_data.date_of_birth,
        email=user_data.email,
        hashed_password=hashed_password,
        status="active",
        type=0
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Log the account creation
    await log_account_change(
        session=session,
        user_id=new_user.id,
        action="created",
        changed_by=new_user.id,
        request=request
    )

    return new_user

@router.get("/me", response_model=UserRead)
async def get_current_account(
    current_user: User = Depends(get_current_user)
):
    """Get current user's account information"""
    return current_user

@router.patch("/me", response_model=UserRead)
async def update_account(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update current user's account information"""

    updated = False

    # Update fields and log changes
    if user_update.firstname is not None and user_update.firstname != current_user.firstname:
        old_value = current_user.firstname
        current_user.firstname = user_update.firstname
        await log_account_change(
            session=session,
            user_id=current_user.id,
            action="updated",
            field_changed="firstname",
            old_value=old_value,
            new_value=user_update.firstname,
            changed_by=current_user.id,
            request=request
        )
        updated = True

    if user_update.lastname is not None and user_update.lastname != current_user.lastname:
        old_value = current_user.lastname
        current_user.lastname = user_update.lastname
        await log_account_change(
            session=session,
            user_id=current_user.id,
            action="updated",
            field_changed="lastname",
            old_value=old_value,
            new_value=user_update.lastname,
            changed_by=current_user.id,
            request=request
        )
        updated = True

    if user_update.date_of_birth is not None and user_update.date_of_birth != current_user.date_of_birth:
        old_value = str(current_user.date_of_birth) if current_user.date_of_birth else None
        current_user.date_of_birth = user_update.date_of_birth
        await log_account_change(
            session=session,
            user_id=current_user.id,
            action="updated",
            field_changed="date_of_birth",
            old_value=old_value,
            new_value=str(user_update.date_of_birth),
            changed_by=current_user.id,
            request=request
        )
        updated = True

    if user_update.email is not None and user_update.email != current_user.email:
        # Check if new email is already in use
        existing_email = session.exec(
            select(User).where(User.email == user_update.email, User.id != current_user.id)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

        old_value = current_user.email
        current_user.email = user_update.email
        await log_account_change(
            session=session,
            user_id=current_user.id,
            action="updated",
            field_changed="email",
            old_value=old_value,
            new_value=user_update.email,
            changed_by=current_user.id,
            request=request
        )
        updated = True

    if updated:
        current_user.updated_at = datetime.utcnow()
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    return current_user

@router.post("/reset-password")
async def reset_password(
    password_reset: PasswordReset,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Reset current user's password"""

    # Verify old password
    if not verify_password(password_reset.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Update password
    current_user.hashed_password = hash_password(password_reset.new_password)
    current_user.updated_at = datetime.utcnow()
    session.add(current_user)
    session.commit()

    # Log password reset
    await log_account_change(
        session=session,
        user_id=current_user.id,
        action="updated",
        field_changed="password",
        old_value="[REDACTED]",
        new_value="[REDACTED]",
        changed_by=current_user.id,
        request=request
    )

    return {"message": "Password reset successfully"}

@router.delete("/me")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete current user's account"""

    # Log the deletion before removing
    await log_account_change(
        session=session,
        user_id=current_user.id,
        action="deleted",
        changed_by=current_user.id,
        request=request
    )

    # Delete user
    session.delete(current_user)
    session.commit()

    return {"message": "Account deleted successfully"}

# Admin endpoints
def get_admin_user(current_user: User = Depends(get_current_user)):
    """Dependency to verify admin privileges"""
    if current_user.type != 1:  # Assuming type 1 is admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

@router.patch("/admin/{user_id}/status", dependencies=[Depends(get_admin_user)])
async def admin_update_account_status(
    user_id: int,
    status_update: AccountStatusUpdate,
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Admin endpoint to enable/disable user accounts"""

    # Validate status value
    if status_update.status not in ["active", "inactive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'active' or 'inactive'"
        )

    # Get target user
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update status
    old_status = user.status
    user.status = status_update.status
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()

    # Log the status change
    action = "activated" if status_update.status == "active" else "deactivated"
    await log_account_change(
        session=session,
        user_id=user.id,
        action=action,
        field_changed="status",
        old_value=old_status,
        new_value=status_update.status,
        changed_by=current_user.id,
        request=request
    )

    return {"message": f"User account {action} successfully"}

@router.post("/admin/{user_id}/reset-password", dependencies=[Depends(get_admin_user)])
async def admin_reset_password(
    user_id: int,
    password_reset: AdminPasswordReset,
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Admin endpoint to reset user password"""

    # Get target user
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.hashed_password = hash_password(password_reset.new_password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()

    # Log password reset
    await log_account_change(
        session=session,
        user_id=user.id,
        action="updated",
        field_changed="password",
        old_value="[REDACTED]",
        new_value="[REDACTED]",
        changed_by=current_user.id,
        request=request
    )

    return {"message": "Password reset successfully"}

@router.delete("/admin/{user_id}", dependencies=[Depends(get_admin_user)])
async def admin_delete_account(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Admin endpoint to delete user accounts"""

    # Get target user
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Don't allow admin to delete themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account via admin endpoint"
        )

    # Log the deletion
    await log_account_change(
        session=session,
        user_id=user.id,
        action="deleted",
        changed_by=current_user.id,
        request=request
    )

    # Delete user
    session.delete(user)
    session.commit()

    return {"message": "User account deleted successfully"}
