"""Approval storage and credential resolution."""

from app.composition.lifecycle import provider
from app.composition.providers.environment import get_workspace
from app.composition.providers.settings import get_settings
from app.security import (
    ApprovalStore,
    CredentialProvider,
    EnvironmentCredentialProvider,
    FileApprovalStore,
)


@provider
def get_approval_store() -> ApprovalStore:
    """Persist approval requests independently from transient API requests."""

    settings = get_settings()
    return FileApprovalStore(
        get_workspace(settings).root / ".runtime" / "approvals",
        ttl_seconds=settings.approval_ttl_seconds,
    )


@provider
def get_credential_provider() -> CredentialProvider:
    """Return the runtime-only resolver; no credential values enter agent context."""

    return EnvironmentCredentialProvider()
