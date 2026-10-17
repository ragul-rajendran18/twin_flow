
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import WarehouseAisle, WarehouseEvent
from ..schemas import (
    WarehouseEventCreate,
    WarehouseEventResponse,
    WarehouseEventBatchResult,
)


class AisleNotFoundError(Exception):
    pass


class DuplicateEventError(Exception):
    pass


class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    def get_aisle_by_code(
        self, aisle_code: str
    ) -> WarehouseAisle | None:
        return self.db.execute(
            select(WarehouseAisle).where(
                WarehouseAisle.aisle_code == aisle_code
            )
        ).scalar_one_or_none()

    def event_exists(self, event_id: str) -> bool:
        return (
            self.db.execute(
                select(WarehouseEvent.id).where(
                    WarehouseEvent.event_id == event_id
                )
            ).scalar_one_or_none()
            is not None
        )

    def ingest_event(
        self, event_data: WarehouseEventCreate
    ) -> Tuple[str, WarehouseEvent | None]:
        aisle = self.get_aisle_by_code(event_data.aisle_code)

        if not aisle:
            return "not_found", None

        if not aisle.is_active:
            return "inactive", None

        if self.event_exists(event_data.event_id):
            return "duplicate", None

        timestamp = event_data.event_timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        db_event = WarehouseEvent(
            event_id=event_data.event_id,
            aisle_id=aisle.id,
            occupancy=event_data.occupancy,
            agv_count=event_data.agv_count,
            queue_length=event_data.queue_length,
            order_volume=event_data.order_volume,
            conveyor_load=event_data.conveyor_load,
            event_timestamp=timestamp,
            received_at=datetime.now(timezone.utc),
            source=event_data.source,
        )

        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)

        return "inserted", db_event

    def ingest_batch(
        self,
        events: List[WarehouseEventCreate],
        max_batch_size: int = 50,
    ) -> WarehouseEventBatchResult:
        if len(events) > max_batch_size:
            events = events[:max_batch_size]

        inserted = []
        duplicates = []
        errors = []

        for event in events:
            status, db_event = self.ingest_event(event)

            if status == "inserted" and db_event:
                inserted.append(
                    WarehouseEventResponse.model_validate(db_event)
                )
            elif status == "duplicate":
                duplicates.append(event.event_id)
            elif status == "not_found":
                errors.append(
                    f"aisle not found: {event.aisle_code}"
                )
            elif status == "inactive":
                errors.append(
                    f"aisle inactive: {event.aisle_code}"
                )
            else:
                errors.append(
                    f"unknown error for {event.event_id}"
                )

        return WarehouseEventBatchResult(
            inserted_count=len(inserted),
            duplicate_count=len(duplicates),
            rejected_count=len(errors),
            inserted=inserted,
            duplicate_event_ids=duplicates,
            errors=errors,
        )


def create_event(
    db: Session, event_data: WarehouseEventCreate
) -> WarehouseEvent:
    service = IngestionService(db)
    status, event = service.ingest_event(event_data)

    if status == "not_found":
        raise AisleNotFoundError(
            f"Aisle not found: {event_data.aisle_code}"
        )

    if status == "inactive":
        raise AisleNotFoundError(
            f"Aisle is inactive: {event_data.aisle_code}"
        )

    if status == "duplicate":
        raise DuplicateEventError(
            f"Duplicate event: {event_data.event_id}"
        )

    if event is None:
        raise RuntimeError("Event ingestion failed unexpectedly.")

    return event
