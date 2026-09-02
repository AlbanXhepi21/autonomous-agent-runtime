"""Channel-specific delivery of one ready artifact.

Every provider here does exactly one thing: turn a ready ``Artifact`` and a
destination into a sanitized, storable outcome. None of them ever raise for
an ordinary failure -- a bad webhook response, an SMTP rejection -- that is
reported as ``DeliveryAttemptResult(success=False, ...)``; an exception here
means something the caller could not have anticipated (a programming error),
not a delivery that simply did not work.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage

import httpx

from app.artifacts.contracts import Artifact
from app.core.logging import log_event, safe_error_message, safe_observation_value
from app.delivery.contracts import DeliveryAttemptResult
from app.security.credentials import CredentialProvider, SecretReference

_logger = logging.getLogger(__name__)

#: A response body this large tells a reader nothing more than a snippet
#: does, and a provider that echoes back an entire request is not unheard of.
_MAX_RESPONSE_SNIPPET = 500


class DeliveryProvider(ABC):
    """Hand a ready artifact to one destination through one channel."""

    @abstractmethod
    async def send(self, *, artifact: Artifact, destination: str) -> DeliveryAttemptResult: ...


class LinkDeliveryProvider(DeliveryProvider):
    """"Deliver" by resolving where the artifact can already be downloaded.

    Makes no external call and cannot fail transiently -- the link is a pure
    function of the artifact and the configured public base URL. The
    ``destination`` argument exists for interface symmetry with the other
    channels; a link delivery does not send anywhere, it states where to go.
    """

    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def send(self, *, artifact: Artifact, destination: str) -> DeliveryAttemptResult:
        link = f"{self._base_url}/artifacts/{artifact.id}"
        return DeliveryAttemptResult(success=True, provider_metadata={"link": link})


class WebhookDeliveryProvider(DeliveryProvider):
    """POST a description of the ready artifact to a destination URL.

    Sends no attachment and no credential -- only metadata and a link a
    receiver can use to fetch the artifact itself. The response is never
    stored raw: only a status code and a redacted, truncated body snippet
    ever reach ``provider_metadata``, and response headers are never stored
    at all (a webhook endpoint can set arbitrary headers, and none of this
    application's business depends on them).
    """

    def __init__(self, *, client: httpx.AsyncClient, base_url: str, timeout_seconds: float) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def send(self, *, artifact: Artifact, destination: str) -> DeliveryAttemptResult:
        payload = {
            "artifact_id": artifact.id, "name": artifact.name, "media_type": artifact.media_type,
            "size": artifact.size, "link": f"{self._base_url}/artifacts/{artifact.id}",
        }
        try:
            response = await self._client.post(destination, json=payload, timeout=self._timeout)
        except httpx.TimeoutException as error:
            return DeliveryAttemptResult(success=False, retryable=True,
                failure_reason=f"webhook timed out: {safe_error_message(error)}")
        except httpx.HTTPError as error:
            return DeliveryAttemptResult(success=False, retryable=True,
                failure_reason=f"webhook request failed: {safe_error_message(error)}")

        snippet = safe_observation_value(response.text[:_MAX_RESPONSE_SNIPPET])
        metadata = {"status_code": response.status_code, "response_snippet": snippet}
        if response.is_success:
            return DeliveryAttemptResult(success=True, provider_metadata=metadata)
        # A 5xx is the receiver's own transient trouble; a 4xx means this
        # destination or payload will never succeed as sent.
        retryable = response.status_code >= 500
        return DeliveryAttemptResult(
            success=False, retryable=retryable, provider_metadata=metadata,
            failure_reason=f"webhook responded {response.status_code}",
        )

    async def dispose(self) -> None:
        await self._client.aclose()


class EmailDeliveryProvider(DeliveryProvider):
    """Send a link to the artifact by email. Never attaches the file itself.

    Constructed only when SMTP is configured (see
    ``app.composition.providers.delivery.get_email_delivery_provider``) --
    there is no "unconfigured" state to represent here, a caller either has
    one of these or does not.
    """

    def __init__(
        self, *, credentials: CredentialProvider, host: str, port: int, username: str,
        from_address: str, use_tls: bool, base_url: str,
    ) -> None:
        self._credentials = credentials
        self._host = host
        self._port = port
        self._username = username
        self._from_address = from_address
        self._use_tls = use_tls
        self._base_url = base_url.rstrip("/")

    async def send(self, *, artifact: Artifact, destination: str) -> DeliveryAttemptResult:
        link = f"{self._base_url}/artifacts/{artifact.id}"
        message = EmailMessage()
        message["Subject"] = f"Report ready: {artifact.name}"
        message["From"] = self._from_address
        message["To"] = destination
        message.set_content(f"{artifact.name} is ready.\n\nDownload: {link}\n")

        try:
            await asyncio.to_thread(self._send_sync, message)
        except (smtplib.SMTPException, OSError) as error:
            log_event(_logger, logging.WARNING, "email_delivery_failed", error=safe_error_message(error))
            return DeliveryAttemptResult(success=False, retryable=True,
                failure_reason=f"email send failed: {safe_error_message(error)}")
        return DeliveryAttemptResult(success=True, provider_metadata={"link": link})

    def _send_sync(self, message: EmailMessage) -> None:
        password = self._credentials.resolve(SecretReference(name="smtp.default"))
        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and password:
                smtp.login(self._username, password)
            smtp.send_message(message)
