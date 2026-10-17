"""Alert management service.

Deduplication strategy
----------------------
At most one **active** alert exists per ``(aisle_id, alert_type)`` pair. When a
new detection would duplicate an active alert, the existing row is updated
(severity, message, prediction link, timestamp) instead of inserting a new row.
When an aisle recovers (LOW congestion, no bottleneck), active alerts for that
aisle are automatically resolved.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Alert

CONGESTION_LEVEL_TO_SEVERITY = {
    "LOW": "LOW",
    "MODERATE": "MEDIUM",
    "HIGH": "HIGH",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_alert(
    db: Session,
    aisle_id: int,
    prediction_id: int | None,
    alert_type: str,
    severity: str,
    message: str,
) -> tuple[Alert, bool]:
    """Create or update the active alert for ``(aisle_id, alert_type)``.

    Returns ``(alert, created)`` where ``created`` is True for a new row and
    False when an existing active alert was updated.
    """
    existing = (
        db.query(Alert)
        .filter(Alert.aisle_id == aisle_id, Alert.alert_type == alert_type, Alert.status == "ACTIVE")
        .first()
    )
    if existing:
        existing.severity = severity
        existing.message = message
        existing.prediction_id = prediction_id
        existing.created_at = _now()
        db.flush()
        return existing, False

    alert = Alert(
        aisle_id=aisle_id,
        prediction_id=prediction_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        status="ACTIVE",
    )
    db.add(alert)
    db.flush()
    return alert, True


def resolve_aisle_alerts(db: Session, aisle_id: int) -> int:
    """Resolve all active alerts for an aisle. Returns the number resolved."""
    active = (
        db.query(Alert)
        .filter(Alert.aisle_id == aisle_id, Alert.status == "ACTIVE")
        .all()
    )
    now = _now()
    for alert in active:
        alert.status = "RESOLVED"
        alert.resolved_at = now
    if active:
        db.flush()
    return len(active)


def resolve_alert(db: Session, alert: Alert) -> bool:
    """Resolve a single alert. Returns True if it was already resolved."""
    if alert.status == "RESOLVED":
        return True
    alert.status = "RESOLVED"
    alert.resolved_at = _now()
    db.flush()
    return False


def generate_alerts_for_prediction(db: Session, prediction) -> tuple[int, int]:
    """Create/update alerts derived from a saved prediction.

    Returns ``(alerts_created, alerts_updated)``.
    """
    level = prediction.congestion_level
    created = 0
    updated = 0

    if level == "HIGH" or level == "MODERATE":
        severity = CONGESTION_LEVEL_TO_SEVERITY.get(level, "LOW")
        message = (
            f"{severity} congestion predicted for aisle {prediction.aisle_id} "
            f"(probability {prediction.congestion_probability:.2f}). "
            f"Estimated delay {prediction.predicted_delay_minutes:.1f} min."
        )
        _, was_created = upsert_alert(
            db, prediction.aisle_id, prediction.id, "CONGESTION", severity, message
        )
        created += int(was_created)
        updated += int(not was_created)

    if prediction.bottleneck_detected:
        severity = "HIGH" if level == "HIGH" else "MEDIUM"
        message = (
            f"Bottleneck detected at aisle {prediction.aisle_id} "
            f"with projected queue {prediction.predicted_queue_length:.0f} units."
        )
        _, was_created = upsert_alert(
            db, prediction.aisle_id, prediction.id, "BOTTLENECK", severity, message
        )
        created += int(was_created)
        updated += int(not was_created)

    if level == "LOW" and not prediction.bottleneck_detected:
        resolve_aisle_alerts(db, prediction.aisle_id)

    return created, updated
