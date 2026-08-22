"""HTTP-only dependencies.

Everything the application constructs lives in app/composition/; this module
holds only what is meaningful to an HTTP request.
"""

from fastapi import HTTPException

from app.composition import get_settings


def require_developer_mode() -> None:
    """Developer-only UI endpoints remain server-authorized, never frontend-gated."""

    if not get_settings().workbench_developer_mode:
        raise HTTPException(
            status_code=404,
            detail={"code": "developer_mode_disabled", "message": "Developer mode is disabled."},
        )
