"""Health and liveness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.database import check_database_connection
from app.schemas.common import MessageResponse

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> MessageResponse:
    return MessageResponse(message="ok", detail="warehouse-congestion-backend")


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def health_check_db() -> MessageResponse:
    ok = check_database_connection()
    if ok:
        return MessageResponse(message="healthy", detail="database connected")
    return MessageResponse(message="unhealthy", detail="database unavailable")
