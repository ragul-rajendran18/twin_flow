from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    aisle_id: int
    prediction_id: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class AlertResolveResponse(AlertResponse):
    pass
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    id: int
    aisle_id: int
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertResolveResponse(BaseModel):
    message: str
    alert_id: int
    status: str