"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencies import close_memory_resources, get_settings
from app.api.routes.agent import router as agent_router
from app.api.routes.artifacts import router as artifact_router
from app.api.routes.approvals import router as approval_router
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Release application-scoped external resources on shutdown."""

    yield
    await close_memory_resources()


app = FastAPI(title="Autonomous Agent", lifespan=lifespan)
app.include_router(agent_router)
app.include_router(artifact_router)
app.include_router(approval_router)
