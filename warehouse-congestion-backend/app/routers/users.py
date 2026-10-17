"""Administrator-only user management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user, require_role
from app.dependencies import get_session
from app.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserRead, UserRole, UserRoleUpdate, UserStatusUpdate, UserUpdate
from app.services.auth_service import normalize_email
from app.utils.pagination import paginate

router = APIRouter(
    prefix="/users",
    tags=["User management"],
    dependencies=[Depends(get_current_user)],
)
_admin = Depends(require_role(UserRole.ADMIN))


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _protect_last_active_admin(db: Session, user: User, remains_active_admin: bool) -> None:
    if user.role != UserRole.ADMIN.value or not user.is_active or remains_active_admin:
        return
    active_admins = db.execute(
        select(User)
        .where(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
        .with_for_update()
    ).scalars().all()
    if len(active_admins) <= 1:
        raise _error(
            status.HTTP_409_CONFLICT,
            "last_active_admin",
            "The last active administrator cannot be deactivated or demoted.",
        )


@router.get("/", response_model=PaginatedResponse[UserRead], dependencies=[_admin])
def list_users(
    db: Session = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=settings.max_page_size),
) -> PaginatedResponse[UserRead]:
    """List users; administrator only."""
    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = db.execute(
        select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return paginate([UserRead.model_validate(user) for user in users], page, page_size, total)


@router.get("/{user_id}", response_model=UserRead, dependencies=[_admin])
def get_user(user_id: int, db: Session = Depends(get_session)) -> UserRead:
    """Get a user's profile; administrator only."""
    user = db.get(User, user_id)
    if user is None:
        raise _error(status.HTTP_404_NOT_FOUND, "user_not_found", "User was not found.")
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead, dependencies=[_admin])
def update_user(
    user_id: int,
    update: UserUpdate,
    db: Session = Depends(get_session),
) -> UserRead:
    """Update a user's name and/or email; administrator only."""
    user = db.get(User, user_id)
    if user is None:
        raise _error(status.HTTP_404_NOT_FOUND, "user_not_found", "User was not found.")

    values = update.model_dump(exclude_unset=True)
    if "email" in values:
        values["email"] = normalize_email(str(values["email"]))
        duplicate = db.scalar(select(User.id).where(User.email == values["email"], User.id != user_id))
        if duplicate is not None:
            raise _error(status.HTTP_409_CONFLICT, "email_in_use", "An account with this email already exists.")
    for field, value in values.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _error(status.HTTP_409_CONFLICT, "email_in_use", "An account with this email already exists.") from exc
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserRead, dependencies=[_admin])
def update_user_status(
    user_id: int,
    update: UserStatusUpdate,
    db: Session = Depends(get_session),
) -> UserRead:
    """Activate or deactivate a user; administrator only."""
    user = db.get(User, user_id)
    if user is None:
        raise _error(status.HTTP_404_NOT_FOUND, "user_not_found", "User was not found.")
    _protect_last_active_admin(db, user, remains_active_admin=update.is_active)
    user.is_active = update.is_active
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserRead, dependencies=[_admin])
def update_user_role(
    user_id: int,
    update: UserRoleUpdate,
    db: Session = Depends(get_session),
) -> UserRead:
    """Assign a role; administrator only and the last active admin is protected."""
    user = db.get(User, user_id)
    if user is None:
        raise _error(status.HTTP_404_NOT_FOUND, "user_not_found", "User was not found.")
    _protect_last_active_admin(
        db,
        user,
        remains_active_admin=(update.role == UserRole.ADMIN),
    )
    user.role = update.role.value
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
