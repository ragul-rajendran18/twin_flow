
from __future__ import annotations

from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from ..models import WarehouseAisle, WarehouseEvent, Prediction, Alert
from ..schemas.aisle import AisleStatus


def get_latest_event(
    db: Session,
    aisle_id: int,
) -> WarehouseEvent | None:
    """Get the latest event for a specific aisle."""
    return (
        db.execute(
            select(WarehouseEvent)
            .where(WarehouseEvent.aisle_id == aisle_id)
            .order_by(
                desc(WarehouseEvent.event_timestamp),
                desc(WarehouseEvent.received_at),
            )
        )
        .scalars()
        .first()
    )


def latest_event_per_aisle(
    db: Session,
    active_only: bool = True,
) -> list[WarehouseEvent]:
    """Return the latest event for each eligible aisle."""
    aisles_query = select(WarehouseAisle)

    if active_only:
        aisles_query = aisles_query.where(
            WarehouseAisle.is_active == True
        )

    aisles = db.execute(aisles_query).scalars().all()
    events: list[WarehouseEvent] = []

    for aisle in aisles:
        event = get_latest_event(db, aisle.id)

        if event is not None:
            events.append(event)

    return events


def latest_prediction_per_aisle(
    db: Session,
    aisle_ids: list[int] | None = None,
) -> dict[int, Prediction]:
    """Return the latest prediction for each aisle."""
    query = select(Prediction).order_by(
        desc(Prediction.created_at),
        desc(Prediction.id),
    )

    if aisle_ids is not None:
        if not aisle_ids:
            return {}

        query = query.where(
            Prediction.aisle_id.in_(aisle_ids)
        )

    rows = db.execute(query).scalars().all()

    latest: dict[int, Prediction] = {}

    for prediction in rows:
        if prediction.aisle_id not in latest:
            latest[prediction.aisle_id] = prediction

    return latest


def get_warehouse_overview(db: Session) -> dict[str, Any]:
    """Get warehouse overview and current congestion statistics."""
    total_aisles = (
        db.execute(
            select(func.count()).select_from(WarehouseAisle)
        ).scalar()
        or 0
    )

    active_aisles = (
        db.execute(
            select(func.count())
            .select_from(WarehouseAisle)
            .where(WarehouseAisle.is_active == True)
        ).scalar()
        or 0
    )

    active_alerts = (
        db.execute(
            select(func.count())
            .select_from(Alert)
            .where(Alert.status == "ACTIVE")
        ).scalar()
        or 0
    )

    aisles = (
        db.execute(
            select(WarehouseAisle)
            .where(WarehouseAisle.is_active == True)
        )
        .scalars()
        .all()
    )

    normal = 0
    moderate = 0
    high = 0

    occupancy_sum = 0.0
    agvs_sum = 0
    queue_sum = 0
    latest_events: list[WarehouseEvent] = []
    last_updated = None

    for aisle in aisles:
        event = get_latest_event(db, aisle.id)

        if event is None:
            normal += 1
            continue

        latest_events.append(event)

        if (
            last_updated is None
            or event.event_timestamp > last_updated
        ):
            last_updated = event.event_timestamp

        occupancy_sum += float(event.occupancy)
        agvs_sum += event.agv_count
        queue_sum += event.queue_length

        latest_level = db.execute(
            select(Prediction.congestion_level)
            .where(Prediction.aisle_id == aisle.id)
            .order_by(
                desc(Prediction.created_at),
                desc(Prediction.id),
            )
        ).scalars().first()

        if latest_level == "HIGH":
            high += 1
        elif latest_level == "MODERATE":
            moderate += 1
        else:
            normal += 1

    average_occupancy = (
        round(occupancy_sum / len(latest_events), 2)
        if latest_events
        else 0.0
    )

    return {
        "total_aisles": total_aisles,
        "active_aisles": active_aisles,
        "normal_aisles": normal,
        "moderate_aisles": moderate,
        "high_congestion_aisles": high,
        "active_alerts": active_alerts,
        "average_occupancy": average_occupancy,
        "total_agvs": agvs_sum,
        "total_queue_length": queue_sum,
        "last_updated": last_updated,
    }


def get_warehouse_aisle_statuses(db: Session) -> list[AisleStatus]:
    """Return the latest event and prediction for every aisle."""
    aisles = (
        db.execute(select(WarehouseAisle).order_by(WarehouseAisle.aisle_code))
        .scalars()
        .all()
    )
    latest_predictions = latest_prediction_per_aisle(
        db, [aisle.id for aisle in aisles]
    )

    statuses = []
    for aisle in aisles:
        status = AisleStatus.model_validate(aisle)
        event = get_latest_event(db, aisle.id)
        if event is not None:
            status.latest_event_timestamp = event.event_timestamp
            status.occupancy = float(event.occupancy)
            status.agv_count = event.agv_count
            status.queue_length = event.queue_length
            status.order_volume = event.order_volume
            status.conveyor_load = float(event.conveyor_load)

        prediction = latest_predictions.get(aisle.id)
        status.congestion_level = (
            prediction.congestion_level if prediction is not None else None
        )
        statuses.append(status)

    return statuses
