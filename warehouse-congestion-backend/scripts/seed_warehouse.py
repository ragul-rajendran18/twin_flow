import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.utils.dummy_data import AISLE_CONFIG
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import WarehouseAisle


def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        count = 0
        existing = set()
        for a in db.query(WarehouseAisle.aisle_code).all():
            existing.add(a[0])
        for cfg in AISLE_CONFIG:
            if cfg["aisle_code"] in existing:
                continue
            a = WarehouseAisle(**cfg)
            db.add(a)
            count += 1
        db.commit()
        print(f"Seeded {count} aisles; existing preserved.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="No-op; preserved by default")
    args = parser.parse_args()
    seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
