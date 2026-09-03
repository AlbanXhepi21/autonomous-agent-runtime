"""HTTP-only dependencies.

Everything the application constructs lives in app/composition/; this module
holds only what is meaningful to an HTTP request.
"""

import hmac
from uuid import UUID

from fastapi import Depends, HTTPException, Path, Request

from app.composition import get_auth_service, get_settings, get_tenancy_service
from app.identity.contracts import Session, User
from app.identity.service import AccountDisabledError, AuthService, SessionInvalidError
from app.identity.tokens import hash_token
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission
from app.tenancy.service import (
    MembershipDisabledError,
    MembershipNotFoundError,
    TenancyService,
    WorkspaceInactiveError,
    WorkspaceNotFoundError,
)

#: Names are shared with app.api.routes.auth, which is the only place that
#: sets or clears them; every other consumer only ever reads.
SESSION_COOKIE_NAME = "session_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def require_developer_mode() -> None:
    """Developer-only UI endpoints remain server-authorized, never frontend-gated."""

    if not get_settings().workbench_developer_mode:
        raise HTTPException(
            status_code=404,
            detail={"code": "developer_mode_disabled", "message": "Developer mode is disabled."},
        )


async def get_current_session(
    request: Request, service: AuthService = Depends(get_auth_service),
) -> Session:
    """Resolve and refresh the caller's session from the session cookie.

    This is the one place a session cookie is read; every authenticated
    dependency below builds on it, so there is exactly one way a request
    becomes "signed in."
    """

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail={"code": "not_authenticated", "message": "Sign in required."})
    try:
        return await service.validate_session(session_token=token)
    except SessionInvalidError as error:
        raise HTTPException(
            status_code=401,
            detail={"code": "session_invalid", "message": "Your session has expired. Sign in again."},
        ) from error


async def get_current_user(
    session: Session = Depends(get_current_session), service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the active, enabled user behind an already-validated session."""

    try:
        return await service.user_for_session(session)
    except AccountDisabledError as error:
        raise HTTPException(
            status_code=403, detail={"code": "account_disabled", "message": "This account has been disabled."},
        ) from error


async def require_csrf(request: Request, session: Session = Depends(get_current_session)) -> None:
    """Reject a cookie-authenticated mutation with no matching CSRF header.

    A browser attaches the session cookie automatically to any cross-site
    request; the CSRF header does not travel unless application code adds
    it, which a third-party page cannot do. Checked against the token minted
    for *this* session (stored server-side as ``csrf_token_hash``), not a
    bare double-submit cookie comparison, so a cookie set by an unrelated
    origin under the same parent domain cannot forge a match.
    """

    header = request.headers.get(CSRF_HEADER_NAME)
    if not header or not hmac.compare_digest(hash_token(header), session.csrf_token_hash):
        raise HTTPException(status_code=403, detail={"code": "csrf_invalid", "message": "Missing or invalid CSRF token."})


async def get_tenant_context(
    workspace_id: UUID = Path(...), user: User = Depends(get_current_user),
    service: TenancyService = Depends(get_tenancy_service),
) -> TenantContext:
    """The one authoritative tenant-context resolver.

    Every tenant-scoped route depends on this -- directly or via
    ``require_permission`` -- rather than looking up membership itself.
    ``WorkspaceNotFoundError``/``WorkspaceInactiveError``/
    ``MembershipNotFoundError`` all become 404: a caller with no standing in
    a workspace cannot distinguish "does not exist" from "exists but you
    were never invited." A membership that exists but was disabled is a
    403 instead -- the caller already knows the workspace exists.
    """

    try:
        return await service.get_context(user=user, workspace_id=workspace_id)
    except (WorkspaceNotFoundError, WorkspaceInactiveError, MembershipNotFoundError) as error:
        raise HTTPException(
            status_code=404, detail={"code": "unknown_workspace", "message": "Workspace not found."},
        ) from error
    except MembershipDisabledError as error:
        raise HTTPException(
            status_code=403, detail={"code": "membership_disabled", "message": "Your membership in this workspace is disabled."},
        ) from error


def require_permission(permission: Permission):
    """Build a dependency that resolves tenant context and enforces one permission.

    The only place a route ever asks "is this caller allowed to do X" --
    against the centralized ``app.tenancy.permissions.ROLE_PERMISSIONS``
    mapping, never by comparing a role name inline.
    """

    async def dependency(context: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not context.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail={"code": "permission_denied", "message": f"Missing permission: {permission.value}"},
            )
        return context

    return dependency
