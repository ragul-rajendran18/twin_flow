"""Alert routes."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.core.dependencies import get_current_user, require_role
from app.models import Alert, WarehouseAisle
from app.schemas.alert import AlertRead, AlertResolveResponse
from app.schemas.common import PaginatedResponse
from app.services.alert_service import resolve_alert
from app.schemas.user import UserRole
from app.utils.pagination import paginate

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
    dependencies=[Depends(get_current_user)],
)

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@router.get("", response_model=PaginatedResponse[AlertRead])
def list_alerts(
    db: Session = Depends(get_session),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    aisle_code: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1),
) -> PaginatedResponse[AlertRead]:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must be <= end_time"
        )
    q = db.query(Alert)
    if status_filter:
        q = q.filter(Alert.status == status_filter.upper())
    if severity:
        q = q.filter(Alert.severity == severity.upper())
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type.upper())
    if aisle_code:
        aisle = db.query(WarehouseAisle).filter_by(aisle_code=aisle_code).first()
        q = q.filter(Alert.aisle_id == (aisle.id if aisle else -1))
    if start_time:
        q = q.filter(Alert.created_at >= start_time)
    if end_time:
        q = q.filter(Alert.created_at <= end_time)
    total = q.count()
    rows = (
        q.order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [AlertRead.model_validate(a) for a in rows]
    return paginate(items, page, page_size, total)


@router.get("/active", response_model=list[AlertRead])
def list_active_alerts(db: Session = Depends(get_session)) -> list[AlertRead]:
    rows = db.query(Alert).filter(Alert.status == "ACTIVE").all()
    rows.sort(key=lambda a: (SEVERITY_ORDER.get(a.severity, 99), -a.created_at.timestamp(), -a.id))
    return [AlertRead.model_validate(a) for a in rows]


@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertResolveResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
def resolve_alert_endpoint(alert_id: int, db: Session = Depends(get_session)) -> AlertResolveResponse:
    alert = db.query(Alert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    already = resolve_alert(db, alert)
    db.commit()
    db.refresh(alert)
    return AlertResolveResponse(
        message="Alert was already resolved" if already else "Alert resolved",
        alert_id=alert.id,
        status=alert.status,
    )
