"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.dependencies import get_settings
from app.api.routes.agent import router as agent_router
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)
app = FastAPI(title="Autonomous Agent")
app.include_router(agent_router)
