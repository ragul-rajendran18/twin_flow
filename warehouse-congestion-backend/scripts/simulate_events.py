import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.utils.dummy_data import generate_synthetic_events, AISLE_CONFIG
from app.services.ingestion_service import IngestionService
from app.database import SessionLocal
from app.schemas import WarehouseEventCreate


def simulate(n=20, scenario="mixed", seed=None):
    db = SessionLocal()
    try:
        svc = IngestionService(db)
        aisles = [a["aisle_code"] for a in AISLE_CONFIG]
        events = generate_synthetic_events(aisles, n, scenario, seed)
        result = svc.ingest_batch([WarehouseEventCreate(**e) for e in events])
        print(result.model_dump())
        return 0
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--scenario", default="mixed")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    return simulate(args.n, args.scenario, args.seed)


if __name__ == "__main__":
    sys.exit(main())
