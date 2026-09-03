"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.approvals import router as approval_router
from app.api.routes.artifacts import router as artifact_router
from app.api.routes.auth import router as auth_router
from app.api.routes.config import router as config_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.datasources import router as datasources_router
from app.api.routes.deliveries import router as deliveries_router
from app.api.routes.memory import router as memory_router
from app.api.routes.reports import router as saved_reports_router
from app.api.routes.scheduled_reports import router as scheduled_reports_router
from app.api.routes.schema import router as schema_router
from app.api.routes.traces import router as trace_router
from app.api.routes.users import router as users_router
from app.api.routes.workspaces import invitations_router
from app.api.routes.workspaces import router as workspaces_router
from app.composition import get_settings, shutdown
from app.core.logging import configure_logging

ROUTERS = (
    auth_router,
    users_router,
    workspaces_router,
    invitations_router,
    agent_router,
    artifact_router,
    approval_router,
    trace_router,
    analytics_router,
    conversations_router,
    saved_reports_router,
    scheduled_reports_router,
    deliveries_router,
    datasources_router,
    schema_router,
    memory_router,
    config_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Configure process-wide logging on startup and release resources on shutdown."""

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    yield
    await shutdown()


def create_app() -> FastAPI:
    """Build the application without touching process-wide state.

    Logging is configured by the lifespan rather than here, so constructing the
    app to read its routes or schema does not pin the "app" logger's level and
    stop propagation, which would silence log capture everywhere else.
    """

    settings = get_settings()
    application = FastAPI(title="Autonomous Agent", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origin_items),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Last-Event-ID", "X-CSRF-Token"],
    )
    for router in ROUTERS:
        application.include_router(router)
    return application
