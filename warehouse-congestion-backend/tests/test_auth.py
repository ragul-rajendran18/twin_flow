from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.core.security import JWT_ALGORITHM, create_access_token, verify_password
from app.models import User
from app.schemas.user import UserCreate, UserRole
from app.services.auth_service import create_user

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def clean_users(db_session):
    db_session.query(User).delete()
    db_session.commit()


def _create_user(db_session, email: str, role: UserRole) -> User:
    return create_user(
        db_session,
        UserCreate(full_name=f"{role.value.title()} User", email=email, password=PASSWORD),
        role=role,
    )


def _authorization(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def test_registration_hashes_password_and_rejects_duplicate(client, db_session):
    body = {"full_name": "New Operator", "email": "New.Operator@example.com", "password": PASSWORD}
    response = client.post("/api/v1/auth/register", json={**body, "role": "admin"})
    assert response.status_code == 201
    assert response.json()["role"] == "operator"
    assert "hashed_password" not in response.json()

    stored_user = db_session.query(User).filter_by(email="new.operator@example.com").one()
    assert stored_user.hashed_password != PASSWORD
    assert verify_password(PASSWORD, stored_user.hashed_password)
    assert client.post("/api/v1/auth/register", json=body).status_code == 409


def test_registration_validates_email_and_password(client):
    invalid_email = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Bad Email", "email": "not-an-email", "password": PASSWORD},
    )
    short_password = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Short Password", "email": "short@example.com", "password": "short"},
    )
    assert invalid_email.status_code == 422
    assert short_password.status_code == 422
    assert '"input"' not in short_password.text


def test_login_me_and_invalid_or_expired_tokens(client, db_session):
    user = _create_user(db_session, "login@example.com", UserRole.OPERATOR)

    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "not-the-password"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email.upper(), "password": PASSWORD},
    )
    assert invalid.status_code == 401
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == user.email
    assert "hashed_password" not in profile.json()

    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid"},
    ).status_code == 401

    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": str(user.id), "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    ).status_code == 401


def test_password_change_requires_current_password(client, db_session):
    user = _create_user(db_session, "password@example.com", UserRole.OPERATOR)
    headers = _authorization(user)
    wrong = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong-current-password", "new_password": "a-new-password-123"},
    )
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "a-new-password-123"},
    )
    assert wrong.status_code == 400
    assert changed.status_code == 200
    db_session.refresh(user)
    assert verify_password("a-new-password-123", user.hashed_password)


def test_role_permissions_and_existing_warehouse_routes(client, db_session, sample_aisle):
    admin = _create_user(db_session, "admin@example.com", UserRole.ADMIN)
    manager = _create_user(db_session, "manager@example.com", UserRole.MANAGER)
    operator = _create_user(db_session, "operator@example.com", UserRole.OPERATOR)
    admin_headers = _authorization(admin)
    manager_headers = _authorization(manager)
    operator_headers = _authorization(operator)

    assert client.get("/api/v1/users/", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/users/", headers=manager_headers).status_code == 403
    assert client.get("/api/v1/users/", headers=operator_headers).status_code == 403
    assert client.get("/api/v1/aisles", headers=operator_headers).status_code == 200
    assert client.get("/api/v1/warehouse/aisles", headers=manager_headers).status_code == 200

    aisle_body = {
        "aisle_code": "AISLE_NEW",
        "aisle_name": "New Aisle",
        "capacity": 100,
        "zone": "ZONE_TEST",
        "is_active": True,
    }
    assert client.post("/api/v1/aisles", json=aisle_body, headers=manager_headers).status_code == 403
    assert client.post("/api/v1/aisles", json=aisle_body, headers=admin_headers).status_code == 201

    event = {
        "event_id": "manager-event",
        "aisle_code": sample_aisle.aisle_code,
        "occupancy": 30,
        "agv_count": 1,
        "queue_length": 0,
        "order_volume": 1,
        "conveyor_load": 20,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    assert client.post("/api/v1/ingestion/events", json=event, headers=manager_headers).status_code == 201
    event["event_id"] = "operator-event"
    assert client.post("/api/v1/ingestion/events", json=event, headers=operator_headers).status_code == 403

    users_page = client.get("/api/v1/users/?page=1&page_size=1", headers=admin_headers)
    assert users_page.status_code == 200
    assert users_page.json()["page_size"] == 1
    assert all("hashed_password" not in item for item in users_page.json()["items"])
    assert client.get("/api/v1/users/?page=0", headers=admin_headers).status_code == 422


def test_admin_can_assign_roles_and_last_active_admin_is_protected(client, db_session):
    admin = _create_user(db_session, "root@example.com", UserRole.ADMIN)
    operator = _create_user(db_session, "promote@example.com", UserRole.OPERATOR)
    headers = _authorization(admin)

    promoted = client.patch(
        f"/api/v1/users/{operator.id}/role",
        json={"role": "manager"},
        headers=headers,
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "manager"
    assert "hashed_password" not in promoted.json()

    blocked = client.patch(
        f"/api/v1/users/{admin.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert blocked.status_code == 409


def test_admin_can_update_user_details_and_status(client, db_session):
    admin = _create_user(db_session, "edit-admin@example.com", UserRole.ADMIN)
    operator = _create_user(db_session, "edit-user@example.com", UserRole.OPERATOR)
    admin_headers = _authorization(admin)
    operator_headers = _authorization(operator)

    updated = client.patch(
        f"/api/v1/users/{operator.id}",
        json={"full_name": "Updated Operator", "email": "updated@example.com"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Operator"
    assert updated.json()["email"] == "updated@example.com"
    assert "hashed_password" not in updated.json()
    assert client.get(
        f"/api/v1/users/{operator.id}",
        headers=admin_headers,
    ).status_code == 200

    duplicate = client.patch(
        f"/api/v1/users/{operator.id}",
        json={"email": admin.email},
        headers=admin_headers,
    )
    assert duplicate.status_code == 409

    deactivated = client.patch(
        f"/api/v1/users/{operator.id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deactivated.status_code == 200
    assert client.get("/api/v1/auth/me", headers=operator_headers).status_code == 403

    reactivated = client.patch(
        f"/api/v1/users/{operator.id}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert reactivated.status_code == 200
    assert client.get("/api/v1/auth/me", headers=operator_headers).status_code == 200


def test_inactive_user_cannot_use_protected_endpoints(client, db_session):
    user = _create_user(db_session, "inactive@example.com", UserRole.OPERATOR)
    token_headers = _authorization(user)
    user.is_active = False
    db_session.commit()

    assert client.get("/api/v1/auth/me", headers=token_headers).status_code == 403
    assert client.get("/api/v1/aisles", headers=token_headers).status_code == 403
