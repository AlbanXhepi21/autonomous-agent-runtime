"""Workspace and membership endpoints.

Every mutating route pairs a permission dependency
(``require_permission(Permission.X)``) with ``require_csrf`` -- the same
"cookie-authenticated mutation" pattern ``app.api.routes.auth`` already
uses. No route compares a role name; ``require_permission`` is the only
place a caller's standing is checked, backed by
``app.tenancy.permissions.ROLE_PERMISSIONS``.
"""

from __future__ import annotations

import os
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies import get_current_user, get_tenant_context, require_csrf, require_permission
from app.api.schemas.auth import MessageResponse
from app.api.schemas.tenancy import (
    AcceptInvitationRequest,
    AuditLogEntryResponse,
    AuditLogListResponse,
    ChangeRoleRequest,
    InvitationResponse,
    InviteMemberRequest,
    MembershipListResponse,
    MembershipResponse,
    ReportPreferencesResponse,
    ReportPreferencesUpdateRequest,
    TransferOwnershipRequest,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.api.schemas.users import UserSettingsResponse
from app.artifacts.store import ArtifactStore
from app.audit.contracts import AuditLogEntry
from app.composition import (
    get_artifact_store,
    get_auth_service,
    get_membership_store,
    get_tenancy_service,
    get_workspace_store,
)
# Aliased: this module already defines a route handler named ``get_workspace``
# (the GET /{workspace_id} endpoint below) -- importing the composition
# provider under its real name would silently shadow it at module scope.
from app.composition import get_workspace as get_environment_workspace
from app.environment.workspace import Workspace as EnvironmentWorkspace
from app.identity.contracts import User
from app.identity.service import AuthService
from app.tenancy.context import TenantContext
from app.tenancy.contracts import Invitation, Membership, ReportPreferences, Workspace
from app.tenancy.permissions import Permission
from app.tenancy.service import (
    AdminCannotManageOwnerError,
    DuplicateInvitationError,
    DuplicateMembershipError,
    InvitationEmailMismatchError,
    InvitationInvalidError,
    LastOwnerError,
    MembershipNotFoundError,
    OwnerRequiredError,
    SlugAlreadyExistsError,
    TenancyService,
)
from app.tenancy.store import (
    MembershipStore,
    ReportPreferencesVersionConflictError,
    WorkspaceStore,
    WorkspaceVersionConflictError,
)

#: A profile image is a small, purely cosmetic upload -- capped well below
#: the general artifact size ceiling rather than sharing it.
_MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024
_ALLOWED_PROFILE_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])
invitations_router = APIRouter(prefix="/api/v1/invitations", tags=["workspaces"])


def _workspace_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id, name=workspace.name, slug=workspace.slug, logo_ref=workspace.logo_ref,
        is_active=workspace.is_active, default_timezone=workspace.default_timezone,
        default_locale=workspace.default_locale, default_currency=workspace.default_currency,
        fiscal_year_start_month=workspace.fiscal_year_start_month, number_format=workspace.number_format,
        date_format=workspace.date_format, version=workspace.version,
        created_at=workspace.created_at, updated_at=workspace.updated_at,
    )


def _report_preferences_response(preferences: ReportPreferences) -> ReportPreferencesResponse:
    return ReportPreferencesResponse(
        workspace_id=preferences.workspace_id, default_template=preferences.default_template,
        default_output_format=preferences.default_output_format, default_theme=preferences.default_theme,
        default_narrative_policy=preferences.default_narrative_policy,
        evidence_appendix_enabled=preferences.evidence_appendix_enabled,
        technical_sql_appendix_enabled=preferences.technical_sql_appendix_enabled,
        version=preferences.version, created_at=preferences.created_at, updated_at=preferences.updated_at,
    )


def _audit_entry_response(entry: AuditLogEntry) -> AuditLogEntryResponse:
    return AuditLogEntryResponse(
        id=entry.id, actor_user_id=entry.actor_user_id, workspace_id=entry.workspace_id,
        event_type=entry.event_type, metadata=entry.metadata, created_at=entry.created_at,
    )


def _version_conflict(error: WorkspaceVersionConflictError | ReportPreferencesVersionConflictError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": "version_conflict",
            "message": f"Expected version {error.expected}, but the stored version is {error.actual}.",
            "expected_version": error.expected, "actual_version": error.actual,
        },
    )


def _membership_response(membership: Membership) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id, user_id=membership.user_id, workspace_id=membership.workspace_id,
        role=membership.role, status=membership.status, invited_by=membership.invited_by,
        joined_at=membership.joined_at, created_at=membership.created_at, updated_at=membership.updated_at,
    )


def _invitation_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id, workspace_id=invitation.workspace_id, email=invitation.email, role=invitation.role,
        invited_by=invitation.invited_by, created_at=invitation.created_at, expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at, revoked_at=invitation.revoked_at,
    )


# -- create / list / read / update ------------------------------------------------


@router.post("", response_model=WorkspaceResponse, status_code=201, dependencies=[Depends(require_csrf)])
async def create_workspace(
    request: WorkspaceCreateRequest, user: User = Depends(get_current_user),
    service: TenancyService = Depends(get_tenancy_service),
) -> WorkspaceResponse:
    try:
        workspace, _ = await service.create_workspace(
            name=request.name, slug=request.slug, owner_user_id=user.id, logo_ref=request.logo_ref,
            default_timezone=request.default_timezone, default_locale=request.default_locale,
            default_currency=request.default_currency,
        )
    except SlugAlreadyExistsError as error:
        raise HTTPException(
            status_code=409, detail={"code": "slug_already_exists", "message": "That workspace slug is already taken."},
        ) from error
    return _workspace_response(workspace)


@router.get("", response_model=WorkspaceListResponse)
async def list_my_workspaces(
    user: User = Depends(get_current_user), memberships: MembershipStore = Depends(get_membership_store),
    workspace_store: WorkspaceStore = Depends(get_workspace_store),
) -> WorkspaceListResponse:
    """Every workspace the caller has any (even disabled) standing in."""

    own_memberships = await memberships.list_for_user(user_id=user.id)
    workspaces = [await workspace_store.get(item.workspace_id) for item in own_memberships]
    return WorkspaceListResponse(items=[_workspace_response(item) for item in workspaces if item is not None])


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
) -> WorkspaceResponse:
    return _workspace_response(context.workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse, dependencies=[Depends(require_csrf)])
async def update_workspace(
    workspace_id: UUID, request: WorkspaceUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.UPDATE_TENANT_SETTINGS)),
    service: TenancyService = Depends(get_tenancy_service),
) -> WorkspaceResponse:
    changes = request.model_dump(exclude_unset=True, exclude={"expected_version"})
    try:
        workspace = await service.update_settings(
            workspace_id=workspace_id, expected_version=request.expected_version, changes=changes,
            actor_user_id=context.user.id,
        )
    except WorkspaceVersionConflictError as error:
        raise _version_conflict(error) from error
    return _workspace_response(workspace)


@router.post("/{workspace_id}/deactivate", response_model=WorkspaceResponse, dependencies=[Depends(require_csrf)])
async def deactivate_workspace(
    workspace_id: UUID, context: TenantContext = Depends(require_permission(Permission.DEACTIVATE_TENANT)),
    service: TenancyService = Depends(get_tenancy_service),
) -> WorkspaceResponse:
    try:
        workspace = await service.deactivate_workspace(
            workspace_id=workspace_id, acting_role=context.role, acting_user_id=context.user.id,
        )
    except OwnerRequiredError as error:
        raise HTTPException(
            status_code=403, detail={"code": "owner_required", "message": "Only an owner may deactivate a workspace."},
        ) from error
    return _workspace_response(workspace)


@router.post("/{workspace_id}/leave", response_model=MessageResponse, dependencies=[Depends(require_csrf)])
async def leave_workspace(
    workspace_id: UUID, context: TenantContext = Depends(get_tenant_context),
    service: TenancyService = Depends(get_tenancy_service),
) -> MessageResponse:
    """Any active member may leave -- no specific permission is required beyond membership itself."""

    try:
        await service.leave_workspace(workspace_id=workspace_id, user_id=context.user.id)
    except LastOwnerError as error:
        raise HTTPException(
            status_code=409, detail={"code": "last_owner", "message": "The last owner cannot leave the workspace."},
        ) from error
    return MessageResponse(message="You have left the workspace.")


@router.post("/{workspace_id}/transfer-ownership", response_model=MembershipResponse, dependencies=[Depends(require_csrf)])
async def transfer_ownership(
    workspace_id: UUID, request: TransferOwnershipRequest,
    context: TenantContext = Depends(require_permission(Permission.TRANSFER_OWNERSHIP)),
    service: TenancyService = Depends(get_tenancy_service),
) -> MembershipResponse:
    try:
        membership = await service.transfer_ownership(
            workspace_id=workspace_id, from_user_id=context.user.id, to_user_id=request.to_user_id,
            acting_role=context.role,
        )
    except OwnerRequiredError as error:
        raise HTTPException(
            status_code=403, detail={"code": "owner_required", "message": "Only an owner may transfer ownership."},
        ) from error
    except MembershipNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "unknown_member", "message": "That user is not an active member of this workspace."},
        ) from error
    return _membership_response(membership)


# -- members ------------------------------------------------------------------


@router.get("/{workspace_id}/members", response_model=MembershipListResponse)
async def list_members(
    workspace_id: UUID, context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    memberships: MembershipStore = Depends(get_membership_store),
) -> MembershipListResponse:
    items = await memberships.list_for_workspace(workspace_id=workspace_id)
    return MembershipListResponse(items=[_membership_response(item) for item in items])


@router.post("/{workspace_id}/members/invite", response_model=InvitationResponse, status_code=201, dependencies=[Depends(require_csrf)])
async def invite_member(
    workspace_id: UUID, request: InviteMemberRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_MEMBERS)),
    service: TenancyService = Depends(get_tenancy_service),
) -> InvitationResponse:
    try:
        invitation = await service.invite_member(
            workspace_id=workspace_id, email=request.email, role=request.role,
            invited_by_user_id=context.user.id, inviter_role=context.role,
        )
    except AdminCannotManageOwnerError as error:
        raise HTTPException(
            status_code=403, detail={"code": "owner_required", "message": "Only an owner may invite a new owner."},
        ) from error
    except DuplicateInvitationError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "duplicate_invitation", "message": "There is already a pending invitation for that email."},
        ) from error
    return _invitation_response(invitation)


@router.patch("/{workspace_id}/members/{user_id}", response_model=MembershipResponse, dependencies=[Depends(require_csrf)])
async def change_member_role(
    workspace_id: UUID, user_id: UUID, request: ChangeRoleRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_MEMBERS)),
    service: TenancyService = Depends(get_tenancy_service),
) -> MembershipResponse:
    try:
        membership = await service.change_role(
            workspace_id=workspace_id, target_user_id=user_id, new_role=request.role, acting_role=context.role,
            acting_user_id=context.user.id,
        )
    except MembershipNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "unknown_member", "message": "That user is not a member of this workspace."}) from error
    except AdminCannotManageOwnerError as error:
        raise HTTPException(status_code=403, detail={"code": "owner_required", "message": str(error)}) from error
    except LastOwnerError as error:
        raise HTTPException(status_code=409, detail={"code": "last_owner", "message": str(error)}) from error
    return _membership_response(membership)


@router.delete("/{workspace_id}/members/{user_id}", response_model=MembershipResponse, dependencies=[Depends(require_csrf)])
async def remove_member(
    workspace_id: UUID, user_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_MEMBERS)),
    service: TenancyService = Depends(get_tenancy_service),
) -> MembershipResponse:
    try:
        membership = await service.remove_member(
            workspace_id=workspace_id, target_user_id=user_id, acting_role=context.role,
            acting_user_id=context.user.id,
        )
    except MembershipNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "unknown_member", "message": "That user is not a member of this workspace."}) from error
    except AdminCannotManageOwnerError as error:
        raise HTTPException(status_code=403, detail={"code": "owner_required", "message": str(error)}) from error
    except LastOwnerError as error:
        raise HTTPException(status_code=409, detail={"code": "last_owner", "message": str(error)}) from error
    return _membership_response(membership)


# -- report preferences ------------------------------------------------------


@router.get("/{workspace_id}/report-preferences", response_model=ReportPreferencesResponse)
async def get_report_preferences(
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    service: TenancyService = Depends(get_tenancy_service),
) -> ReportPreferencesResponse:
    preferences = await service.get_report_preferences(workspace_id=context.workspace.id)
    return _report_preferences_response(preferences)


@router.patch("/{workspace_id}/report-preferences", response_model=ReportPreferencesResponse, dependencies=[Depends(require_csrf)])
async def update_report_preferences(
    workspace_id: UUID, request: ReportPreferencesUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.UPDATE_TENANT_SETTINGS)),
    service: TenancyService = Depends(get_tenancy_service),
) -> ReportPreferencesResponse:
    changes = request.model_dump(exclude_unset=True, exclude={"expected_version"})
    try:
        preferences = await service.update_report_preferences(
            workspace_id=workspace_id, expected_version=request.expected_version, changes=changes,
            actor_user_id=context.user.id,
        )
    except ReportPreferencesVersionConflictError as error:
        raise _version_conflict(error) from error
    return _report_preferences_response(preferences)


# -- audit log ----------------------------------------------------------------


@router.get("/{workspace_id}/audit-log", response_model=AuditLogListResponse)
async def list_audit_log(
    limit: int = 50, offset: int = 0,
    context: TenantContext = Depends(require_permission(Permission.UPDATE_TENANT_SETTINGS)),
    service: TenancyService = Depends(get_tenancy_service),
) -> AuditLogListResponse:
    """Gated the same as settings edits -- an audit trail is at least as
    sensitive as the settings it records changes to.
    """

    entries = await service.list_audit_log(
        workspace_id=context.workspace.id, limit=min(limit, 200), offset=max(offset, 0),
    )
    return AuditLogListResponse(items=[_audit_entry_response(entry) for entry in entries])


# -- profile image (through the existing artifact system) --------------------


@router.post("/{workspace_id}/profile-image", response_model=UserSettingsResponse, dependencies=[Depends(require_csrf)])
async def set_profile_image(
    file: UploadFile,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    artifacts: ArtifactStore = Depends(get_artifact_store), auth: AuthService = Depends(get_auth_service),
    workspace: EnvironmentWorkspace = Depends(get_environment_workspace),
) -> UserSettingsResponse:
    """Store an avatar through the same registry every other document goes
    through: written into the shared environment workspace, then registered
    as a workspace-scoped artifact. The caller's own membership in
    ``workspace_id`` is what authorizes writing into that workspace's store;
    the image itself is a personal setting, not a workspace resource, so
    ``User.profile_image_artifact_id``/``profile_image_workspace_id`` is
    where the pointer actually lives.
    """

    if file.content_type not in _ALLOWED_PROFILE_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_image_type", "message": f"Unsupported image type: {file.content_type}."},
        )
    data = await file.read(_MAX_PROFILE_IMAGE_BYTES + 1)
    if len(data) > _MAX_PROFILE_IMAGE_BYTES:
        raise HTTPException(
            status_code=422, detail={"code": "image_too_large", "message": "Profile images are limited to 5 MB."},
        )

    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}[file.content_type]
    relative_path = f"profile-images/{context.user.id}/avatar.{extension}"
    resolved = workspace.resolve(relative_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", dir=resolved.parent, delete=False) as temporary:
        temporary.write(data)
        temporary_path = temporary.name
    os.replace(temporary_path, resolved)

    artifact = await artifacts.register(
        workspace_id=context.workspace.id, run_id=f"profile-image-{context.user.id}", source_path=relative_path,
        name=f"avatar.{extension}", artifact_type="user_profile_image", media_type=file.content_type,
    )
    user = await auth.set_profile_image(
        user_id=context.user.id, artifact_id=UUID(artifact.id), workspace_id=context.workspace.id,
    )
    return UserSettingsResponse(
        id=user.id, email=user.email, pending_email=user.pending_email, display_name=user.display_name,
        preferred_timezone=user.preferred_timezone, preferred_locale=user.preferred_locale,
        profile_image_artifact_id=user.profile_image_artifact_id,
        profile_image_workspace_id=user.profile_image_workspace_id,
        is_active=user.is_active, email_verified=user.email_verified,
        created_at=user.created_at, updated_at=user.updated_at, last_login_at=user.last_login_at,
    )


# -- invitations (not workspace-scoped: the caller isn't a member yet) --------------


@invitations_router.post("/accept", response_model=MembershipResponse)
async def accept_invitation(
    request: AcceptInvitationRequest, user: User = Depends(get_current_user),
    service: TenancyService = Depends(get_tenancy_service),
) -> MembershipResponse:
    try:
        membership = await service.accept_invitation(token=request.token, accepting_user=user)
    except InvitationInvalidError as error:
        raise HTTPException(
            status_code=400, detail={"code": "invalid_invitation", "message": "This invitation is invalid or has expired."},
        ) from error
    except InvitationEmailMismatchError as error:
        raise HTTPException(
            status_code=403,
            detail={"code": "invitation_email_mismatch", "message": "This invitation was sent to a different email address."},
        ) from error
    except DuplicateMembershipError as error:
        raise HTTPException(
            status_code=409, detail={"code": "already_a_member", "message": "You are already a member of this workspace."},
        ) from error
    return _membership_response(membership)
