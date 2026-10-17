"""Simulation and synthetic data routes.

These endpoints reproduce the kind of operational data that real warehouse
equipment (AGVs, conveyors, scanners) could generate in the future. No physical
hardware or external service is required.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user, require_role
from app.dependencies import get_session
from app.models import WarehouseAisle, WarehouseEvent
from app.schemas.warehouse_event import WarehouseEventCreate
from app.schemas.user import UserRole
from app.services.ingestion_service import AisleNotFoundError, DuplicateEventError, create_event
from app.utils.dummy_data import (
    AISLE_CONFIG as DUMMY_AISLES,
    SCENARIO_MAP as SCENARIOS,
    generate_synthetic_events as generate_events,
)

router = APIRouter(
    prefix="/simulation",
    tags=["Simulation"],
    dependencies=[Depends(get_current_user)],
)
_operational_write = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))


class SeedRequest(BaseModel):
    include_historical_events: bool = Field(
        default=False, description="Also generate an initial batch of synthetic events"
    )
    historical_events: int = Field(default=0, ge=0, le=1000)
    scenario: str = Field(default="mixed")
    seed: int | None = Field(default=42)


class SeedResponse(BaseModel):
    aisles_created: int
    aisles_skipped: int
    events_created: int
    events_skipped: int
    message: str


class GenerateRequest(BaseModel):
    number_of_events: int = Field(default=20, ge=1)
    scenario: str = Field(default="mixed")
    seed: int | None = Field(default=42)


class GenerateResponse(BaseModel):
    requested: int
    generated: int
    inserted: int
    duplicates: int
    rejected: int
    scenario: str
    message: str


class StepRequest(BaseModel):
    aisle_codes: list[str] | None = Field(default=None, description="Aisles to advance; omit for all active aisles")
    scenario: str = Field(default="mixed")
    seed: int | None = Field(default=None)


class StatusResponse(BaseModel):
    seeded_aisles: int
    active_aisles: int
    total_events: int
    latest_event_timestamp: datetime | None
    supported_scenarios: list[str]
    max_simulation_events: int
    message: str


def _persist_events(db: Session, events: list[dict]) -> tuple[int, int, int]:
    """Persist generated events, tolerating duplicates. Returns (inserted, duplicates, rejected)."""
    inserted = duplicates = rejected = 0
    for payload in events:
        try:
            create_event(db, WarehouseEventCreate.model_validate(payload))
            inserted += 1
        except DuplicateEventError:
            db.rollback()
            duplicates += 1
        except AisleNotFoundError:
            db.rollback()
            rejected += 1
    db.commit()
    return inserted, duplicates, rejected


@router.post(
    "/seed",
    response_model=SeedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_operational_write],
)
def seed_simulation(request: SeedRequest, db: Session = Depends(get_session)) -> SeedResponse:
    if request.scenario not in SCENARIOS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown scenario")

    created = skipped = 0
    for seed_aisle in DUMMY_AISLES:
        existing = db.query(WarehouseAisle).filter_by(aisle_code=seed_aisle["aisle_code"]).first()
        if existing:
            skipped += 1
            continue
        db.add(
            WarehouseAisle(
                aisle_code=seed_aisle["aisle_code"],
                aisle_name=seed_aisle["aisle_name"],
                capacity=seed_aisle["capacity"],
                zone=seed_aisle["zone"],
                is_active=seed_aisle["is_active"],
            )
        )
        created += 1
    db.commit()

    events_created = events_skipped = 0
    if request.include_historical_events and request.historical_events > 0:
        codes = [a["aisle_code"] for a in DUMMY_AISLES if a["is_active"]]
        events = generate_events(codes, request.historical_events, request.scenario, request.seed)
        events_created, events_skipped, _rejected = _persist_events(db, events)

    return SeedResponse(
        aisles_created=created,
        aisles_skipped=skipped,
        events_created=events_created,
        events_skipped=events_skipped,
        message=(
            "Seed complete. Existing aisles are preserved; repeated runs are safe."
        ),
    )


@router.post(
    "/generate",
    response_model=GenerateResponse,
    dependencies=[_operational_write],
)
def generate_simulation(request: GenerateRequest, db: Session = Depends(get_session)) -> GenerateResponse:
    if request.scenario not in SCENARIOS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown scenario")
    if request.number_of_events > settings.max_simulation_events:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"number_of_events exceeds maximum of {settings.max_simulation_events}",
        )
    codes = [a.aisle_code for a in db.query(WarehouseAisle).filter(WarehouseAisle.is_active.is_(True)).all()]
    if not codes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active aisles found. Run /api/v1/simulation/seed first.",
        )
    events = generate_events(codes, request.number_of_events, request.scenario, request.seed)
    inserted, duplicates, rejected = _persist_events(db, events)
    return GenerateResponse(
        requested=request.number_of_events,
        generated=len(events),
        inserted=inserted,
        duplicates=duplicates,
        rejected=rejected,
        scenario=request.scenario,
        message="Synthetic events generated and persisted via the ingestion service.",
    )


@router.post(
    "/step",
    response_model=GenerateResponse,
    dependencies=[_operational_write],
)
def step_simulation(request: StepRequest, db: Session = Depends(get_session)) -> GenerateResponse:
    if request.scenario not in SCENARIOS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown scenario")
    if request.aisle_codes:
        q = db.query(WarehouseAisle).filter(WarehouseAisle.aisle_code.in_(request.aisle_codes))
    else:
        q = db.query(WarehouseAisle).filter(WarehouseAisle.is_active.is_(True))
    codes = [a.aisle_code for a in q.all()]
    if not codes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching aisles to advance")
    events = generate_events(codes, len(codes), request.scenario, request.seed)
    inserted, duplicates, rejected = _persist_events(db, events)
    return GenerateResponse(
        requested=len(codes),
        generated=len(events),
        inserted=inserted,
        duplicates=duplicates,
        rejected=rejected,
        scenario=request.scenario,
        message="Advanced simulation by one interval for the selected aisles.",
    )


@router.get("/status", response_model=StatusResponse)
def simulation_status(db: Session = Depends(get_session)) -> StatusResponse:
    total_aisles = db.query(func.count(WarehouseAisle.id)).scalar() or 0
    active_aisles = (
        db.query(func.count(WarehouseAisle.id)).filter(WarehouseAisle.is_active.is_(True)).scalar() or 0
    )
    total_events = db.query(func.count(WarehouseEvent.id)).scalar() or 0
    latest_ts = db.query(func.max(WarehouseEvent.event_timestamp)).scalar()
    return StatusResponse(
        seeded_aisles=total_aisles,
        active_aisles=active_aisles,
        total_events=total_events,
        latest_event_timestamp=latest_ts,
        supported_scenarios=list(SCENARIOS),
        max_simulation_events=settings.max_simulation_events,
        message="Manual simulation endpoints only; no background process runs.",
    )
