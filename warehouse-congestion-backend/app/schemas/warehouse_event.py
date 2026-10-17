from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class WarehouseEventBase(BaseModel):
    event_id: str = Field(min_length=1, max_length=36)
    aisle_code: str = Field(min_length=3, max_length=50)
    occupancy: float = Field(ge=0, le=100)
    agv_count: int = Field(ge=0)
    queue_length: int = Field(ge=0)
    order_volume: int = Field(ge=0)
    conveyor_load: float = Field(ge=0, le=100)
    event_timestamp: datetime
    source: str = Field(default="simulation", min_length=1, max_length=50)


class WarehouseEventCreate(WarehouseEventBase):
    pass


class WarehouseEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: str
    aisle_id: int
    occupancy: float
    agv_count: int
    queue_length: int
    order_volume: int
    conveyor_load: float
    event_timestamp: datetime
    received_at: datetime
    source: str
    created_at: datetime


class WarehouseEventBatch(BaseModel):
    events: List[WarehouseEventCreate]


class WarehouseEventBatchResult(BaseModel):
    inserted_count: int
    duplicate_count: int
    rejected_count: int
    inserted: List[WarehouseEventResponse] = []
    duplicate_event_ids: List[str] = []
    errors: List[str] = []

class BatchEventItemResult(BaseModel):
    index: int
    event_id: str
    status: str
    detail: Optional[str] = None

WarehouseEventRead = WarehouseEventResponse