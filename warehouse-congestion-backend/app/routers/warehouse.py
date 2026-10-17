"""Warehouse dashboard routes."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.core.dependencies import get_current_user
from app.models import WarehouseAisle, WarehouseEvent
from app.schemas.common import PaginatedResponse
from app.schemas.warehouse_event import WarehouseEventRead
from app.services.warehouse_service import (
    get_warehouse_aisle_statuses,
    get_warehouse_overview,
)
from app.utils.pagination import paginate

router = APIRouter(
    prefix="/warehouse",
    tags=["Warehouse"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/overview")
def warehouse_overview(db: Session = Depends(get_session)):
    """Aggregated statistics from the latest event per active aisle.

    Aisles without any events are excluded from the occupancy/AGV/queue
    aggregates and are counted as ``normal`` (they are not congested).
    """
    return get_warehouse_overview(db)


@router.get("/aisles")
def warehouse_aisles(db: Session = Depends(get_session)):
    """Latest operational status for every aisle."""
    return get_warehouse_aisle_statuses(db)


@router.get("/events", response_model=PaginatedResponse[WarehouseEventRead])
def warehouse_events(
    db: Session = Depends(get_session),
    aisle_code: str | None = Query(default=None),
    source: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1),
) -> PaginatedResponse[WarehouseEventRead]:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must be <= end_time"
        )
    q = db.query(WarehouseEvent)
    if aisle_code:
        aisle = db.query(WarehouseAisle).filter_by(aisle_code=aisle_code).first()
        q = q.filter(WarehouseEvent.aisle_id == (aisle.id if aisle else -1))
    if source:
        q = q.filter(WarehouseEvent.source == source)
    if start_time:
        q = q.filter(WarehouseEvent.event_timestamp >= start_time)
    if end_time:
        q = q.filter(WarehouseEvent.event_timestamp <= end_time)
    total = q.count()
    rows = (
        q.order_by(WarehouseEvent.event_timestamp.desc(), WarehouseEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [WarehouseEventRead.model_validate(e) for e in rows]
    return paginate(items, page, page_size, total)
