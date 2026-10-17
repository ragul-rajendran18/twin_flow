"""Warehouse event ingestion routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user, require_role
from app.dependencies import get_session
from app.schemas.warehouse_event import (
    WarehouseEventBatch,
    WarehouseEventBatchResult,
    WarehouseEventCreate,
    WarehouseEventResponse,
)
from app.schemas.user import UserRole
from app.services.ingestion_service import (
    AisleNotFoundError,
    DuplicateEventError,
    IngestionService,
    create_event,
)

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(get_current_user)],
)
_operational_write = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))


@router.post(
    "/events",
    response_model=WarehouseEventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_operational_write],
)
def ingest_event(
    event: WarehouseEventCreate,
    db: Session = Depends(get_session),
) -> WarehouseEventResponse:
    try:
        return WarehouseEventResponse.model_validate(create_event(db, event))
    except AisleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DuplicateEventError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/events/batch",
    response_model=WarehouseEventBatchResult,
    dependencies=[_operational_write],
)
def ingest_batch(
    batch: WarehouseEventBatch,
    db: Session = Depends(get_session),
) -> WarehouseEventBatchResult:
    if len(batch.events) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch exceeds maximum size of {settings.max_batch_size}",
        )
    return IngestionService(db).ingest_batch(
        batch.events, max_batch_size=settings.max_batch_size
    )
