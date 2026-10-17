"""Main application factory."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import check_database_connection, engine
from app.routers import (
    alerts,
    aisles,
    health,
    ingestion,
    predictions,
    simulation,
    auth,
    users,
    warehouse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan hooks.

    Does not drop/recreate tables. Tables are managed by Alembic migrations.
    """
    try:
        logger.info("Starting application: %s v%s", settings.app_name, settings.app_version)
    except Exception:
        pass
    yield
    try:
        engine.dispose()
    except Exception:
        pass


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Backend for AI-based congestion and bottleneck prediction in a smart warehouse. "
            "Uses simulated events and PostgreSQL; provides ingestion, ML predictions, "
            "alerts, and dashboard APIs for a React frontend."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "Authentication", "description": "Registration and login are public; `/me` and password changes require a valid bearer JWT."},
            {"name": "User management", "description": "All endpoints require an active administrator bearer JWT."},
            {"name": "Aisles", "description": "Reads require an active user. Creating or updating aisles is administrator-only."},
            {"name": "Ingestion", "description": "Requires authentication. Event ingestion writes are available to admins and managers."},
            {"name": "Warehouse", "description": "Warehouse monitoring reads require an active user of any role."},
            {"name": "Predictions", "description": "Reads require an active user; running predictions is available to admins and managers."},
            {"name": "Alerts", "description": "Reads require an active user; resolving alerts is available to admins and managers."},
            {"name": "Simulation", "description": "Status reads require an active user; simulation writes are available to admins and managers."},
            {"name": "Health", "description": "Public application and database liveness checks."},
        ],
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(aisles.router, prefix="/api/v1")
    app.include_router(ingestion.router, prefix="/api/v1")
    app.include_router(warehouse.router, prefix="/api/v1")
    app.include_router(predictions.router, prefix="/api/v1")
    app.include_router(alerts.router, prefix="/api/v1")
    app.include_router(simulation.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        if request.url.path in {
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/change-password",
        }:
            errors = [{key: value for key, value in error.items() if key != "input"} for error in errors]
        return JSONResponse(
            status_code=422,
            content={"detail": jsonable_encoder(errors)},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception("Database error during request")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal database error", "error_code": "database_error"},
        )

    @app.exception_handler(Exception)
    async def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error during request")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_code": "internal_error"},
        )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
        }

    return app


app = create_application()

__all__ = ["app", "create_application"]
