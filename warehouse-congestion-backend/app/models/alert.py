from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, func, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_aisle_id", "aisle_id"),
        Index("ix_alerts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aisle_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouse_aisles.id", ondelete="RESTRICT"), nullable=False)
    prediction_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("predictions.prediction_id", ondelete="SET NULL"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    aisle = relationship("WarehouseAisle")
