"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import close_memory_resources, get_settings
from app.api.routes.agent import router as agent_router
from app.api.routes.artifacts import router as artifact_router
from app.api.routes.approvals import router as approval_router
from app.api.routes.traces import router as trace_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.schema import router as schema_router
from app.api.routes.memory import router as memory_router
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Release application-scoped external resources on shutdown."""

    yield
    await close_memory_resources()


app = FastAPI(title="Autonomous Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.analytics_ui_frontend_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Last-Event-ID"],
)
app.include_router(agent_router)
app.include_router(artifact_router)
app.include_router(approval_router)
app.include_router(trace_router)
app.include_router(analytics_router)
app.include_router(conversations_router)
app.include_router(schema_router)
app.include_router(memory_router)
