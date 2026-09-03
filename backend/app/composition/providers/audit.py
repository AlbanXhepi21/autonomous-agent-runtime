"""The audit log: shared between identity and tenancy, selected by TENANCY_BACKEND.

Not its own backend flag -- an audit trail is tenancy-adjacent (most entries
carry a ``workspace_id``) and does not warrant a third independently
selectable persistence knob alongside IDENTITY_BACKEND/TENANCY_BACKEND.
"""

from app.audit.store import AuditLogStore, InMemoryAuditLogStore
from app.composition.lifecycle import provider
from app.composition.providers.persistence import get_runtime_database
from app.composition.providers.settings import get_settings


@provider
def get_audit_log_store() -> AuditLogStore:
    settings = get_settings()
    if settings.tenancy_backend == "in_memory":
        return InMemoryAuditLogStore()
    from app.audit.store import PostgresAuditLogStore

    return PostgresAuditLogStore(get_runtime_database())
