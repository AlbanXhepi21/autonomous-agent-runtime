"""Workspace-connected PostgreSQL data sources: storage, encryption, onboarding."""

from datetime import timedelta

from app.composition.lifecycle import provider
from app.composition.providers.persistence import get_runtime_database
from app.composition.providers.security import get_credential_provider
from app.composition.providers.settings import get_settings
from app.datasources.encryption import FernetSecretCipher, SecretCipher
from app.datasources.service import DataSourceOnboardingService
from app.datasources.store import DataSourceStore, PostgresDataSourceStore


@provider
def get_secret_cipher() -> SecretCipher:
    """Return the encryptor a data source's password is stored through."""

    return FernetSecretCipher(get_credential_provider())


@provider
def get_data_source_store() -> DataSourceStore:
    """Use the existing runtime PostgreSQL database for data source connections and their catalog."""

    return PostgresDataSourceStore(get_runtime_database())


@provider
def get_data_source_onboarding_service() -> DataSourceOnboardingService:
    """Return the orchestrator for onboarding steps that need a live connection."""

    settings = get_settings()
    return DataSourceOnboardingService(
        store=get_data_source_store(), cipher=get_secret_cipher(),
        allow_local_hosts=settings.datasource_allow_local_hosts,
        schema_cache_ttl_seconds=settings.analytics_schema_cache_ttl_seconds,
        freshness_stale_after=timedelta(hours=settings.datasource_freshness_stale_after_hours),
    )
