"""Aisle management routes."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.core.dependencies import get_current_user, require_role
from app.models import WarehouseAisle, WarehouseEvent
from app.schemas.aisle import AisleCreate, AisleRead, AisleStatus, AisleUpdate
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserRole
from app.utils.pagination import paginate

router = APIRouter(
    prefix="/aisles",
    tags=["Aisles"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=AisleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_aisle(aisle_in: AisleCreate, db: Session = Depends(get_session)) -> AisleRead:
    if db.query(WarehouseAisle).filter_by(aisle_code=aisle_in.aisle_code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Aisle with code {aisle_in.aisle_code} already exists",
        )
    aisle = WarehouseAisle(
        aisle_code=aisle_in.aisle_code,
        aisle_name=aisle_in.aisle_name,
        capacity=aisle_in.capacity,
        zone=aisle_in.zone,
        is_active=aisle_in.is_active,
    )
    db.add(aisle)
    db.commit()
    db.refresh(aisle)
    return AisleRead.model_validate(aisle)


@router.get("", response_model=PaginatedResponse[AisleRead])
def list_aisles(
    db: Session = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1),
    zone: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> PaginatedResponse[AisleRead]:
    q = db.query(WarehouseAisle)
    if zone:
        q = q.filter(WarehouseAisle.zone == zone)
    if is_active is not None:
        q = q.filter(WarehouseAisle.is_active.is_(is_active))
    total = q.count()
    aisles = (
        q.order_by(WarehouseAisle.aisle_code)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [AisleRead.model_validate(a) for a in aisles]
    return paginate(items, page, page_size, total)


@router.get("/{aisle_id}", response_model=AisleStatus)
def get_aisle(aisle_id: int, db: Session = Depends(get_session)) -> AisleStatus:
    aisle = db.query(WarehouseAisle).filter_by(id=aisle_id).first()
    if not aisle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aisle not found")
    latest_event = (
        db.query(WarehouseEvent)
        .filter(WarehouseEvent.aisle_id == aisle_id)
        .order_by(WarehouseEvent.event_timestamp.desc(), WarehouseEvent.id.desc())
        .first()
    )
    congestion = None
    if latest_event and latest_event.predictions:
        latest_event.predictions.sort(key=lambda p: p.created_at, reverse=True)
        congestion = latest_event.predictions[0].congestion_level
    status_obj = AisleStatus.model_validate(aisle)
    if latest_event:
        status_obj.latest_event_timestamp = latest_event.event_timestamp
        status_obj.occupancy = float(latest_event.occupancy)
        status_obj.agv_count = latest_event.agv_count
        status_obj.queue_length = latest_event.queue_length
        status_obj.order_volume = latest_event.order_volume
        status_obj.conveyor_load = float(latest_event.conveyor_load)
    status_obj.congestion_level = congestion
    return status_obj


@router.patch(
    "/{aisle_id}",
    response_model=AisleRead,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_aisle(aisle_id: int, aisle_in: AisleUpdate, db: Session = Depends(get_session)) -> AisleRead:
    aisle = db.query(WarehouseAisle).filter_by(id=aisle_id).first()
    if not aisle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aisle not found")
    data = aisle_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(aisle, k, v)
    db.commit()
    db.refresh(aisle)
    return AisleRead.model_validate(aisle)


@router.get("/{aisle_id}/history", response_model=PaginatedResponse)
def aisle_history(
    aisle_id: int,
    db: Session = Depends(get_session),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1),
):
    aisle = db.query(WarehouseAisle).filter_by(id=aisle_id).first()
    if not aisle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aisle not found")
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must be <= end_time")
    q = db.query(WarehouseEvent).filter(WarehouseEvent.aisle_id == aisle_id)
    if start_time:
        q = q.filter(WarehouseEvent.event_timestamp >= start_time)
    if end_time:
        q = q.filter(WarehouseEvent.event_timestamp <= end_time)
    total = q.count()
    events = (
        q.order_by(WarehouseEvent.event_timestamp.desc(), WarehouseEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    from app.schemas.warehouse_event import WarehouseEventRead

    items = [WarehouseEventRead.model_validate(e) for e in events]
    return paginate(items, page, page_size, total)
