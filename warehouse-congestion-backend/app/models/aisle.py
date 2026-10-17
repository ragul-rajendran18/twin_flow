from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class WarehouseAisle(Base):
    __tablename__ = "warehouse_aisles"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="chk_aisle_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aisle_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    aisle_name: Mapped[str] = mapped_column(String(150), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
