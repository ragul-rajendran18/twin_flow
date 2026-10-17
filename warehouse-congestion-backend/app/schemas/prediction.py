
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    aisle_code: Optional[str] = None


class PredictionRunRequest(BaseModel):
    aisle_code: Optional[str] = None


class PredictionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prediction_id: str
    aisle_id: int
    event_id: Optional[str] = None
    congestion_probability: float
    congestion_level: str
    bottleneck_detected: bool
    predicted_queue_length: float
    predicted_delay_minutes: float
    recommendation: str
    model_version: str


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction_id: str
    aisle_id: int
    event_id: Optional[str] = None
    congestion_probability: float
    congestion_level: str
    bottleneck_detected: bool
    predicted_queue_length: float
    predicted_delay_minutes: float
    recommendation: str
    model_version: str
    created_at: datetime


class PredictionResponse(PredictionRead):
    pass


class PredictionDetail(PredictionRead):
    aisle_code: Optional[str] = None
    event: Optional[dict] = None


class PredictionRunResponse(BaseModel):
    model_version: str
    predictions_created: int
    alerts_created: int
    alerts_updated: int
    predictions: list[PredictionRead]
