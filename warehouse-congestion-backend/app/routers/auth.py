"""Public registration/login and authenticated profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import get_session
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserRead, UserRole
from app.services.auth_service import DuplicateEmailError, authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_session)) -> UserRead:
    """Public registration; new accounts always receive the operator role."""
    try:
        user = create_user(db, user_data, role=UserRole.OPERATOR)
    except DuplicateEmailError:
        raise _error(status.HTTP_409_CONFLICT, "email_in_use", "An account with this email already exists.") from None
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_session)) -> TokenResponse:
    """Exchange email and password for a short-lived bearer JWT."""
    user = authenticate_user(db, str(request.email), request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Email or password is incorrect."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    expires_in = settings.jwt_access_token_expire_minutes * 60
    return TokenResponse(access_token=create_access_token(user.id), expires_in=expires_in)


@router.get("/me", response_model=UserRead)
def read_current_user(user: User = Depends(get_current_user)) -> UserRead:
    """Return the authenticated user's profile; requires an active bearer JWT."""
    return UserRead.model_validate(user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> MessageResponse:
    """Change the authenticated user's password after checking the current password."""
    if not verify_password(request.current_password, user.hashed_password):
        raise _error(status.HTTP_400_BAD_REQUEST, "invalid_current_password", "Current password is incorrect.")
    if request.current_password == request.new_password:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "password_unchanged", "New password must differ from the current password.")
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    return MessageResponse(message="Password changed successfully.")
