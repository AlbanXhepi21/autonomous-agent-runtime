"""What the Workbench needs to know about how this server is configured."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.composition import get_settings
from app.config import Settings

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class WorkbenchConfigResponse(BaseModel):
    """Server-owned switches the Workbench reflects in what it offers.

    Advertising a capability is not the same as granting it: the endpoints
    behind developer mode enforce it independently, so this only decides
    whether the Workbench offers a control the server would honour.
    """

    model_config = ConfigDict(extra="forbid")

    developer_mode: bool


@router.get("")
async def get_config(settings: Settings = Depends(get_settings)) -> WorkbenchConfigResponse:
    return WorkbenchConfigResponse(developer_mode=settings.workbench_developer_mode)
