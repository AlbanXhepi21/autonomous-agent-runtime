"""Provider-neutral artifact delivery: a link always works, the rest are opt-in."""

from app.composition.lifecycle import provider
from app.composition.providers.artifacts import get_artifact_store
from app.composition.providers.persistence import get_runtime_database
from app.composition.providers.security import get_credential_provider
from app.composition.providers.settings import get_settings
from app.delivery.contracts import DeliveryChannel
from app.delivery.providers import DeliveryProvider, EmailDeliveryProvider, LinkDeliveryProvider, WebhookDeliveryProvider
from app.delivery.service import DeliveryService
from app.delivery.store import DeliveryStore, PostgresDeliveryStore


@provider
def get_delivery_store() -> DeliveryStore:
    """Use the existing runtime PostgreSQL database for delivery attempts."""

    return PostgresDeliveryStore(get_runtime_database())


@provider
def get_link_delivery_provider() -> LinkDeliveryProvider:
    """Always available -- resolving a link makes no external call."""

    return LinkDeliveryProvider(base_url=get_settings().public_api_base_url)


@provider
def get_webhook_delivery_provider() -> WebhookDeliveryProvider:
    """Own one HTTP client, closed on shutdown like every other resource here."""

    import httpx

    settings = get_settings()
    return WebhookDeliveryProvider(
        client=httpx.AsyncClient(), base_url=settings.public_api_base_url,
        timeout_seconds=settings.webhook_timeout_seconds,
    )


@provider
def get_email_delivery_provider() -> EmailDeliveryProvider | None:
    """Return an SMTP-backed provider only when SMTP is actually configured."""

    settings = get_settings()
    if not settings.email_delivery_configured:
        return None
    return EmailDeliveryProvider(
        credentials=get_credential_provider(), host=settings.smtp_host, port=settings.smtp_port,
        username=settings.smtp_username, from_address=settings.smtp_from_address,
        use_tls=settings.smtp_use_tls, base_url=settings.public_api_base_url,
    )


@provider
def get_delivery_providers() -> dict[DeliveryChannel, DeliveryProvider]:
    """Every channel this deployment can actually deliver through."""

    providers: dict[DeliveryChannel, DeliveryProvider] = {
        "link": get_link_delivery_provider(),
        "webhook": get_webhook_delivery_provider(),
    }
    email = get_email_delivery_provider()
    if email is not None:
        providers["email"] = email
    return providers


@provider
def get_delivery_service() -> DeliveryService:
    """Return the deliver-one-artifact entry point, backed by every configured channel."""

    return DeliveryService(
        artifacts=get_artifact_store(), store=get_delivery_store(), providers=get_delivery_providers(),
    )
