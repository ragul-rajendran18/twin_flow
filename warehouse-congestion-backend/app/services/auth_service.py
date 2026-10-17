from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate, UserRole


class DuplicateEmailError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def create_user(
    db: Session,
    user_data: UserCreate,
    *,
    role: UserRole = UserRole.OPERATOR,
) -> User:
    email = normalize_email(str(user_data.email))
    if db.execute(select(User.id).where(User.email == email)).scalar_one_or_none():
        raise DuplicateEmailError(email)

    user = User(
        full_name=user_data.full_name,
        email=email,
        hashed_password=hash_password(user_data.password),
        role=role.value,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError(email) from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.execute(
        select(User).where(User.email == normalize_email(email))
    ).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        return None
    return user
