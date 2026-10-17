from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AisleBase(BaseModel):
    aisle_code: str = Field(min_length=3, max_length=50)
    aisle_name: str = Field(min_length=3, max_length=150)
    capacity: int = Field(gt=0)
    zone: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class AisleCreate(AisleBase):
    pass


class AisleUpdate(BaseModel):
    aisle_name: Optional[str] = Field(default=None, min_length=3, max_length=150)
    capacity: Optional[int] = Field(default=None, gt=0)
    zone: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_active: Optional[bool] = None


class AisleResponse(AisleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class AisleWithStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aisle_code: str
    aisle_name: str
    capacity: int
    zone: str
    is_active: bool

    latest_event_timestamp: Optional[datetime] = None
    occupancy: Optional[float] = None
    agv_count: Optional[int] = None
    queue_length: Optional[int] = None
    order_volume: Optional[int] = None
    conveyor_load: Optional[float] = None
    congestion_level: Optional[str] = None


class AisleHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    aisle_code: str

AisleRead = AisleResponse
AisleStatus = AisleWithStatus