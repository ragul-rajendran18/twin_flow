"""Shared pytest fixtures.

Test database strategy
----------------------
Tests run against an *isolated* database and never touch production data:

1. If ``TEST_DATABASE_URL`` is set, it is used verbatim.
2. Otherwise the PostgreSQL URL from ``DATABASE_URL`` is reused with a
   ``_test`` suffix (the database is created automatically if missing).
3. If PostgreSQL is unreachable, the suite falls back to a temporary SQLite
   file so the business logic can still be verified offline.

Each test runs inside a transaction that is rolled back afterwards, so tests
are independent and leave no residue.
"""
from __future__ import annotations

import os

# Test-only signing key; production settings must be supplied through the environment.
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "pytest-only-signing-key-never-use-this-outside-tests-0123456789",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register models on Base.metadata)
from app.config import settings
from app.database import Base
from app.dependencies import get_session
from app.main import app


def _candidate_database_urls() -> list[str]:
    urls: list[str] = []
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        urls.append(explicit)
    base = make_url(settings.sync_database_url)
    if base.get_backend_name().startswith("postgresql"):
        urls.append(str(base.set(database=(base.database or "warehouse_db") + "_test")))
    else:
        urls.append(str(base))
    # Final offline fallback.
    urls.append("sqlite+pysqlite:///./.pytest_test.db")
    return urls


def _ensure_postgres_database(test_url: str) -> bool:
    """Create the PostgreSQL test database if it does not exist."""
    url = make_url(test_url)
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
        return True
    except Exception:
        return False
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def test_engine():
    last_error: Exception | None = None
    for url in _candidate_database_urls():
        backend = make_url(url).get_backend_name()
        try:
            if backend.startswith("postgresql"):
                if not _ensure_postgres_database(url):
                    last_error = RuntimeError(f"could not create/connect PostgreSQL test db at {url}")
                    continue
            engine = create_engine(url, future=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
            yield engine
            engine.dispose()
            return
        except Exception as exc:  # pragma: no cover - environment dependent
            last_error = exc
            continue
    pytest.skip(f"No test database available: {last_error}")


@pytest.fixture()
def db_session(test_engine):
    """Yield a session bound to a transaction that is rolled back afterwards."""
    connection = test_engine.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
        future=True,
    )
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_aisle(db_session):
    from app.models import WarehouseAisle

    aisle = WarehouseAisle(
        aisle_code="AISLE_TEST",
        aisle_name="Test Aisle",
        capacity=100,
        zone="ZONE_TEST",
        is_active=True,
    )
    db_session.add(aisle)
    db_session.commit()
    db_session.refresh(aisle)
    return aisle


@pytest.fixture(scope="session")
def ml_artifacts_dir(tmp_path_factory):
    """Train small models into a temporary artifacts directory (session scoped)."""
    from ml.generate_dataset import generate_dataframe, save_dataset
    from ml.train_model import train

    artifacts = tmp_path_factory.mktemp("ml_artifacts")
    dataset_path = artifacts / "dataset.csv"
    save_dataset(generate_dataframe(rows=600, seed=7), dataset_path)
    train(dataset_path, artifacts)
    return artifacts


@pytest.fixture()
def trained_models(ml_artifacts_dir, monkeypatch):
    """Point the global model registry at the freshly trained test artifacts."""
    import ml.predict as predict_module
    from ml.predict import ModelRegistry

    monkeypatch.setattr(predict_module, "_registry", ModelRegistry(ml_artifacts_dir), raising=False)
    return ml_artifacts_dir
