"""Prediction routes."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.core.dependencies import get_current_user, require_role
from app.models import Prediction, WarehouseAisle
from app.schemas.common import PaginatedResponse
from app.schemas.prediction import (
    PredictionDetail,
    PredictionRead,
    PredictionRunRequest,
    PredictionRunResponse,
)
from app.schemas.warehouse_event import WarehouseEventRead
from app.schemas.user import UserRole
from app.services.prediction_service import AisleNotFoundForPrediction, run_predictions
from app.services.warehouse_service import latest_prediction_per_aisle
from app.utils.pagination import paginate
from ml.predict import ModelNotTrainedError

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/run",
    response_model=PredictionRunResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
def run_prediction(
    request: PredictionRunRequest | None = None,
    db: Session = Depends(get_session),
) -> PredictionRunResponse:
    aisle_code = request.aisle_code if request else None
    try:
        result = run_predictions(db, aisle_code)
    except ModelNotTrainedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AisleNotFoundForPrediction as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aisle not found"
        ) from exc
    return PredictionRunResponse(
        model_version=result.model_version,
        predictions_created=result.predictions_created,
        alerts_created=result.alerts_created,
        alerts_updated=result.alerts_updated,
        predictions=[PredictionRead.model_validate(p) for p in result.predictions],
    )


@router.get("/latest", response_model=list[PredictionDetail])
def latest_predictions(
    db: Session = Depends(get_session),
    congestion_level: str | None = Query(default=None),
    aisle_code: str | None = Query(default=None),
) -> list[PredictionDetail]:
    if aisle_code:
        aisle = db.query(WarehouseAisle).filter_by(aisle_code=aisle_code).first()
        aisle_ids = [aisle.id] if aisle else []
    else:
        aisle_ids = None
    predictions = latest_prediction_per_aisle(db, aisle_ids)
    codes = {a.id: a.aisle_code for a in db.query(WarehouseAisle).all()}
    items: list[PredictionDetail] = []
    for p in predictions.values():
        if congestion_level and p.congestion_level != congestion_level.upper():
            continue
        detail = PredictionDetail.model_validate(p)
        detail.aisle_code = codes.get(p.aisle_id)
        items.append(detail)
    items.sort(key=lambda d: d.prediction_id)
    return items


@router.get("/history", response_model=PaginatedResponse[PredictionRead])
def prediction_history(
    db: Session = Depends(get_session),
    aisle_code: str | None = Query(default=None),
    congestion_level: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1),
) -> PaginatedResponse[PredictionRead]:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must be <= end_time"
        )
    q = db.query(Prediction)
    if aisle_code:
        aisle = db.query(WarehouseAisle).filter_by(aisle_code=aisle_code).first()
        q = q.filter(Prediction.aisle_id == (aisle.id if aisle else -1))
    if congestion_level:
        q = q.filter(Prediction.congestion_level == congestion_level.upper())
    if start_time:
        q = q.filter(Prediction.created_at >= start_time)
    if end_time:
        q = q.filter(Prediction.created_at <= end_time)
    total = q.count()
    rows = (
        q.order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [PredictionRead.model_validate(p) for p in rows]
    return paginate(items, page, page_size, total)


@router.get("/{prediction_id}", response_model=PredictionDetail)
def get_prediction(prediction_id: str, db: Session = Depends(get_session)) -> PredictionDetail:
    prediction = db.query(Prediction).filter_by(prediction_id=prediction_id).first()
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    detail = PredictionDetail.model_validate(prediction)
    aisle = db.query(WarehouseAisle).filter_by(id=prediction.aisle_id).first()
    detail.aisle_code = aisle.aisle_code if aisle else None
    if prediction.event is not None:
        detail.event = WarehouseEventRead.model_validate(prediction.event)
    return detail
