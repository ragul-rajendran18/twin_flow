"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-17 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouse_aisles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aisle_code", sa.String(length=50), nullable=False),
        sa.Column("aisle_name", sa.String(length=120), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("zone", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("capacity > 0", name="ck_aisle_capacity_positive"),
    )
    op.create_index("ix_warehouse_aisles_aisle_code", "warehouse_aisles", ["aisle_code"], unique=True)
    op.create_index("ix_warehouse_aisles_zone", "warehouse_aisles", ["zone"])

    op.create_table(
        "warehouse_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("aisle_id", sa.Integer(), nullable=False),
        sa.Column("occupancy", sa.Float(), nullable=False),
        sa.Column("agv_count", sa.Integer(), nullable=False),
        sa.Column("queue_length", sa.Integer(), nullable=False),
        sa.Column("order_volume", sa.Integer(), nullable=False),
        sa.Column("conveyor_load", sa.Float(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="simulation"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["aisle_id"], ["warehouse_aisles.id"], ondelete="CASCADE"),
        sa.CheckConstraint("occupancy >= 0 AND occupancy <= 100", name="ck_event_occupancy_range"),
        sa.CheckConstraint("conveyor_load >= 0 AND conveyor_load <= 100", name="ck_event_conveyor_range"),
        sa.CheckConstraint("agv_count >= 0", name="ck_event_agv_nonnegative"),
        sa.CheckConstraint("queue_length >= 0", name="ck_event_queue_nonnegative"),
        sa.CheckConstraint("order_volume >= 0", name="ck_event_order_nonnegative"),
    )
    op.create_index("ix_warehouse_events_event_id", "warehouse_events", ["event_id"], unique=True)
    op.create_index("ix_events_aisle_id", "warehouse_events", ["aisle_id"])
    op.create_index("ix_events_event_timestamp", "warehouse_events", ["event_timestamp"])
    op.create_index("ix_events_received_at", "warehouse_events", ["received_at"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.String(length=36), nullable=False),
        sa.Column("aisle_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("congestion_probability", sa.Float(), nullable=False),
        sa.Column("congestion_level", sa.String(length=20), nullable=False),
        sa.Column("bottleneck_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("predicted_queue_length", sa.Float(), nullable=False),
        sa.Column("predicted_delay_minutes", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["aisle_id"], ["warehouse_aisles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["warehouse_events.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "congestion_probability >= 0 AND congestion_probability <= 1",
            name="ck_prediction_probability_range",
        ),
        sa.CheckConstraint("predicted_queue_length >= 0", name="ck_prediction_queue_nonnegative"),
        sa.CheckConstraint("predicted_delay_minutes >= 0", name="ck_prediction_delay_nonnegative"),
        sa.CheckConstraint(
            "congestion_level IN ('LOW', 'MODERATE', 'HIGH')",
            name="ck_prediction_congestion_level",
        ),
    )
    op.create_index("ix_predictions_prediction_id", "predictions", ["prediction_id"], unique=True)
    op.create_index("ix_predictions_aisle_id", "predictions", ["aisle_id"])
    op.create_index("ix_predictions_congestion_level", "predictions", ["congestion_level"])
    op.create_index("ix_predictions_created_at", "predictions", ["created_at"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aisle_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["aisle_id"], ["warehouse_aisles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="SET NULL"),
        sa.CheckConstraint("alert_type IN ('CONGESTION', 'BOTTLENECK')", name="ck_alert_type"),
        sa.CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_alert_severity"),
        sa.CheckConstraint("status IN ('ACTIVE', 'RESOLVED')", name="ck_alert_status"),
    )
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_aisle_id", "alerts", ["aisle_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("predictions")
    op.drop_table("warehouse_events")
    op.drop_table("warehouse_aisles")
