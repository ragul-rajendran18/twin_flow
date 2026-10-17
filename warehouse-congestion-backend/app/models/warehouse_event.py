from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, func, CheckConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class WarehouseEvent(Base):
    __tablename__ = "warehouse_events"
    __table_args__ = (
        CheckConstraint("occupancy >= 0 AND occupancy <= 100", name="chk_event_occupancy_range"),
        CheckConstraint("conveyor_load >= 0 AND conveyor_load <= 100", name="chk_event_conveyor_range"),
        CheckConstraint("agv_count >= 0", name="chk_event_agv_nonneg"),
        CheckConstraint("queue_length >= 0", name="chk_event_queue_nonneg"),
        CheckConstraint("order_volume >= 0", name="chk_event_order_nonneg"),
        Index("ix_warehouse_events_aisle_id", "aisle_id"),
        Index("ix_warehouse_events_event_timestamp", "event_timestamp"),
        Index("ix_warehouse_events_received_at", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    aisle_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouse_aisles.id", ondelete="RESTRICT"), nullable=False)
    occupancy: Mapped[float] = mapped_column(Float, nullable=False)
    agv_count: Mapped[int] = mapped_column(Integer, nullable=False)
    queue_length: Mapped[int] = mapped_column(Integer, nullable=False)
    order_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    conveyor_load: Mapped[float] = mapped_column(Float, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="simulation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    aisle = relationship("WarehouseAisle")
