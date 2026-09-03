"""User profile/settings endpoints: display name, locale preferences, and
the two-step, password-reauthenticated email-change flow.

Distinct from ``app.api.routes.auth`` (session/credential mechanics) the
same way ``app.api.routes.workspaces`` is distinct from ``app.api.routes.auth``
for tenants: this router owns *what a signed-in user's account looks like*,
not how they got signed in.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, require_csrf
from app.api.schemas.auth import MessageResponse
from app.api.schemas.users import (
    ConfirmEmailChangeRequest,
    RequestEmailChangeRequest,
    UserSettingsResponse,
    UserSettingsUpdateRequest,
)
from app.composition import get_auth_service
from app.identity.contracts import User
from app.identity.service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    SameEmailError,
    TokenInvalidError,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _settings_response(user: User) -> UserSettingsResponse:
    return UserSettingsResponse(
        id=user.id, email=user.email, pending_email=user.pending_email, display_name=user.display_name,
        preferred_timezone=user.preferred_timezone, preferred_locale=user.preferred_locale,
        profile_image_artifact_id=user.profile_image_artifact_id,
        profile_image_workspace_id=user.profile_image_workspace_id,
        is_active=user.is_active, email_verified=user.email_verified,
        created_at=user.created_at, updated_at=user.updated_at, last_login_at=user.last_login_at,
    )


@router.get("/me", response_model=UserSettingsResponse)
async def get_my_settings(user: User = Depends(get_current_user)) -> UserSettingsResponse:
    return _settings_response(user)


@router.patch("/me", response_model=UserSettingsResponse, dependencies=[Depends(require_csrf)])
async def update_my_settings(
    request: UserSettingsUpdateRequest, user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserSettingsResponse:
    updated = await service.update_profile(
        user_id=user.id, display_name=request.display_name,
        preferred_timezone=request.preferred_timezone, preferred_locale=request.preferred_locale,
    )
    return _settings_response(updated)


@router.post("/me/email-change/request", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def request_email_change(
    request: RequestEmailChangeRequest, user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await service.request_email_change(
            user_id=user.id, new_email=request.new_email, current_password=request.current_password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_credentials", "message": "Current password is incorrect."},
        ) from error
    except SameEmailError as error:
        raise HTTPException(
            status_code=422, detail={"code": "same_email", "message": str(error)},
        ) from error
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "email_already_registered", "message": "An account with that email already exists."},
        ) from error
    return MessageResponse(message="Confirm the change from the link we sent to your new email address.")


@router.post("/me/email-change/confirm", response_model=UserSettingsResponse)
async def confirm_email_change(
    request: ConfirmEmailChangeRequest, service: AuthService = Depends(get_auth_service),
) -> UserSettingsResponse:
    try:
        updated = await service.confirm_email_change(token=request.token)
    except TokenInvalidError as error:
        raise HTTPException(
            status_code=400, detail={"code": "invalid_token", "message": "This link is invalid or has expired."},
        ) from error
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "email_already_registered", "message": "An account with that email already exists."},
        ) from error
    return _settings_response(updated)
