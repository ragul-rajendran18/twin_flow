"""Deterministic recommendation rules based on prediction results.

These are software-generated *suggestions*, not automatic control commands.
"""
from __future__ import annotations

from app.config import settings


def build_recommendation(
    congestion_level: str,
    congestion_probability: float,
    bottleneck_detected: bool,
    predicted_queue_length: float,
    predicted_delay_minutes: float,
    conveyor_load: float | None = None,
) -> str:
    """Return a human-readable operational recommendation."""
    parts: list[str] = []

    if congestion_level == "HIGH" or bottleneck_detected:
        parts.append(
            "HIGH congestion risk: reduce incoming AGV traffic and redirect new "
            "tasks to alternate aisles."
        )
    elif congestion_level == "MODERATE":
        parts.append("MODERATE congestion: monitor occupancy and queue growth closely.")
    else:
        parts.append("LOW congestion: continue normal operations.")

    if predicted_queue_length >= 15:
        parts.append(
            f"Projected queue of {predicted_queue_length:.0f} units: temporarily "
            "limit new orders routed to this aisle."
        )
    elif predicted_queue_length >= 8:
        parts.append(
            f"Projected queue of {predicted_queue_length:.0f} units: stagger order "
            "release to smooth the queue."
        )

    if conveyor_load is not None and conveyor_load >= 85:
        parts.append("High conveyor load: redistribute workload across parallel conveyors.")
    elif conveyor_load is not None and conveyor_load >= 70:
        parts.append("Elevated conveyor load: prepare to redistribute workload.")

    if predicted_delay_minutes >= 10:
        parts.append(
            f"Estimated delay of {predicted_delay_minutes:.0f} minutes: notify the "
            "fulfilment team and re-sequence picks."
        )

    return " ".join(parts)
