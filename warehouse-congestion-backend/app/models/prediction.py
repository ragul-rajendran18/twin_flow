from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric, func, CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("congestion_probability >= 0 AND congestion_probability <= 1", name="chk_pred_prob_range"),
        CheckConstraint("predicted_queue_length >= 0", name="chk_pred_queue_nonneg"),
        CheckConstraint("predicted_delay_minutes >= 0", name="chk_pred_delay_nonneg"),
        Index("ix_predictions_aisle_id", "aisle_id"),
        Index("ix_predictions_congestion_level", "congestion_level"),
        Index("ix_predictions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    aisle_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouse_aisles.id", ondelete="RESTRICT"), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("warehouse_events.event_id", ondelete="SET NULL"), nullable=True)
    congestion_probability: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_level: Mapped[str] = mapped_column(String(20), nullable=False)
    bottleneck_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    predicted_queue_length: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    predicted_delay_minutes: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    aisle = relationship("WarehouseAisle")
    event = relationship("WarehouseEvent", primaryjoin="Prediction.event_id==WarehouseEvent.event_id")
