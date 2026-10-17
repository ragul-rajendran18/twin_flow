"""Interactively create the first administrator without a source-code password."""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.schemas.user import UserCreate, UserRole
from app.services.auth_service import DuplicateEmailError, create_user


def main() -> int:
    db = SessionLocal()
    try:
        existing_admin = db.execute(
            select(User.id).where(User.role == UserRole.ADMIN.value)
        ).scalar_one_or_none()
        if existing_admin is not None:
            print("An administrator account already exists; bootstrap was not run.")
            return 1

        full_name = input("Administrator full name: ").strip()
        email = input("Administrator email: ").strip()
        password = getpass.getpass("Administrator password (12+ characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            print("Passwords do not match.")
            return 1

        try:
            request = UserCreate(full_name=full_name, email=email, password=password)
            user = create_user(db, request, role=UserRole.ADMIN)
        except DuplicateEmailError:
            print("Administrator was not created: an account with that email already exists.")
            return 1
        except ValueError:
            print("Administrator was not created: name, email, or password did not meet requirements.")
            return 1

        print(f"Created administrator account for {user.email} (user id {user.id}).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
