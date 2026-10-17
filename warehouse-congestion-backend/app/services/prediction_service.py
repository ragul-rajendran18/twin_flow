"""Prediction orchestration service.

Fetches the latest event per target aisle, runs the trained models, persists
results and creates/updates alerts. Training never happens here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import Prediction, WarehouseAisle, WarehouseEvent
from app.services.alert_service import generate_alerts_for_prediction
from app.services.recommendation_service import build_recommendation
from app.services.warehouse_service import latest_event_per_aisle
from ml.predict import ModelNotTrainedError, get_model_registry


@dataclass
class PredictionRunResult:
    model_version: str
    predictions_created: int = 0
    alerts_created: int = 0
    alerts_updated: int = 0
    predictions: list[Prediction] = field(default_factory=list)


def _event_features(event: WarehouseEvent) -> dict[str, float]:
    return {
        "occupancy": float(event.occupancy),
        "agv_count": float(event.agv_count),
        "queue_length": float(event.queue_length),
        "order_volume": float(event.order_volume),
        "conveyor_load": float(event.conveyor_load),
    }


def run_predictions(db: Session, aisle_code: str | None = None) -> PredictionRunResult:
    """Run predictions for the latest event of each eligible aisle.

    Raises :class:`ModelNotTrainedError` when artifacts are unavailable so the
    API can return a 503 with clear remediation instructions.
    """
    registry = get_model_registry()
    registry.load()  # raises ModelNotTrainedError if missing

    if aisle_code:
        aisle = db.query(WarehouseAisle).filter_by(aisle_code=aisle_code).first()
        if not aisle:
            raise AisleNotFoundForPrediction(aisle_code)
        events = latest_event_per_aisle(db, active_only=False)
        events = [e for e in events if e.aisle_id == aisle.id]
    else:
        events = latest_event_per_aisle(db, active_only=True)

    result = PredictionRunResult(model_version=registry.model_version)

    for event in events:
        features = _event_features(event)
        model_result = registry.predict(features)

        recommendation = build_recommendation(
            congestion_level=model_result.congestion_level,
            congestion_probability=model_result.congestion_probability,
            bottleneck_detected=model_result.bottleneck_detected,
            predicted_queue_length=model_result.predicted_queue_length,
            predicted_delay_minutes=model_result.predicted_delay_minutes,
            conveyor_load=features["conveyor_load"],
        )

        prediction = Prediction(
            prediction_id=str(uuid.uuid4()),
            aisle_id=event.aisle_id,
            event_id=event.id,
            congestion_probability=model_result.congestion_probability,
            congestion_level=model_result.congestion_level,
            bottleneck_detected=model_result.bottleneck_detected,
            predicted_queue_length=model_result.predicted_queue_length,
            predicted_delay_minutes=model_result.predicted_delay_minutes,
            recommendation=recommendation,
            model_version=model_result.model_version,
        )
        db.add(prediction)
        db.flush()

        created, updated = generate_alerts_for_prediction(db, prediction)
        result.alerts_created += created
        result.alerts_updated += updated

        result.predictions.append(prediction)
        result.predictions_created += 1

    db.commit()
    for prediction in result.predictions:
        db.refresh(prediction)
    return result


class AisleNotFoundForPrediction(ValueError):
    def __init__(self, aisle_code: str) -> None:
        self.aisle_code = aisle_code
        super().__init__(f"Aisle not found: {aisle_code}")


__all__ = ["run_predictions", "PredictionRunResult", "AisleNotFoundForPrediction", "ModelNotTrainedError"]
