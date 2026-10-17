from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

AISLE_CONFIG = [
    {"aisle_code": "AISLE_A", "aisle_name": "Storage Aisle A", "capacity": 100, "zone": "ZONE_1", "is_active": True},
    {"aisle_code": "AISLE_B", "aisle_name": "Picking Aisle B", "capacity": 120, "zone": "ZONE_1", "is_active": True},
    {"aisle_code": "AISLE_C", "aisle_name": "Sorting Aisle C", "capacity": 80, "zone": "ZONE_2", "is_active": True},
    {"aisle_code": "AISLE_D", "aisle_name": "Loading Aisle D", "capacity": 90, "zone": "ZONE_2", "is_active": True},
    {"aisle_code": "AISLE_E", "aisle_name": "Staging Aisle E", "capacity": 110, "zone": "ZONE_3", "is_active": True},
    {"aisle_code": "AISLE_F", "aisle_name": "Buffer Aisle F", "capacity": 75, "zone": "ZONE_3", "is_active": True},
    {"aisle_code": "AISLE_G", "aisle_name": "Return Aisle G", "capacity": 70, "zone": "ZONE_4", "is_active": True},
    {"aisle_code": "AISLE_H", "aisle_name": "Cross Dock H", "capacity": 85, "zone": "ZONE_4", "is_active": True},
]


SCENARIO_MAP = {
    "normal": lambda: {
        "occupancy": random.uniform(30, 55),
        "agv_count": random.randint(1, 3),
        "queue_length": random.randint(1, 5),
        "order_volume": random.randint(5, 12),
        "conveyor_load": random.uniform(25, 55),
    },
    "moderate": lambda: {
        "occupancy": random.uniform(55, 75),
        "agv_count": random.randint(3, 6),
        "queue_length": random.randint(5, 12),
        "order_volume": random.randint(12, 20),
        "conveyor_load": random.uniform(55, 75),
    },
    "high_congestion": lambda: {
        "occupancy": random.uniform(75, 95),
        "agv_count": random.randint(6, 10),
        "queue_length": random.randint(12, 20),
        "order_volume": random.randint(20, 35),
        "conveyor_load": random.uniform(75, 95),
    },
    "mixed": lambda: random.choice([
        {
            "occupancy": random.uniform(30, 55),
            "agv_count": random.randint(1, 3),
            "queue_length": random.randint(1, 5),
            "order_volume": random.randint(5, 12),
            "conveyor_load": random.uniform(25, 55),
        },
        {
            "occupancy": random.uniform(55, 75),
            "agv_count": random.randint(3, 6),
            "queue_length": random.randint(5, 12),
            "order_volume": random.randint(12, 20),
            "conveyor_load": random.uniform(55, 75),
        },
        {
            "occupancy": random.uniform(75, 95),
            "agv_count": random.randint(6, 10),
            "queue_length": random.randint(12, 20),
            "order_volume": random.randint(20, 35),
            "conveyor_load": random.uniform(75, 95),
        },
    ]),
}


def generate_synthetic_events(aisle_codes: List[str], number_of_events: int = 10, scenario: str = "mixed", seed: Optional[int] = None, base_time: Optional[datetime] = None) -> List[Dict]:
    if seed is not None:
        random.seed(seed)
    if base_time is None:
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
    events = []
    for i in range(number_of_events):
        aisle_code = random.choice(aisle_codes) if aisle_codes else random.choice([a["aisle_code"] for a in AISLE_CONFIG])
        gen = SCENARIO_MAP.get(scenario, SCENARIO_MAP["mixed"])()
        event = {
            "event_id": str(uuid.uuid4()),
            "aisle_code": aisle_code,
            "occupancy": round(float(gen["occupancy"]), 2),
            "agv_count": int(gen["agv_count"]),
            "queue_length": int(gen["queue_length"]),
            "order_volume": int(gen["order_volume"]),
            "conveyor_load": round(float(gen["conveyor_load"]), 2),
            "event_timestamp": (base_time + timedelta(minutes=i * 5)).replace(microsecond=0),
            "source": "simulation",
        }
        events.append(event)
    return events
