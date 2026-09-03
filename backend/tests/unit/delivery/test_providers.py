"""Channel providers: link resolution, webhook sanitization, offline for real."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.artifacts.contracts import Artifact, ArtifactStatus
from app.delivery.providers import LinkDeliveryProvider, WebhookDeliveryProvider


def _artifact() -> Artifact:
    return Artifact(
        id="artifact-1", workspace_id=uuid.uuid4(), name="report.pdf", relative_path="artifacts/run/artifact-1/report.pdf",
        artifact_type="report_document", media_type="application/pdf", size=4096, sha256="0" * 64,
        status=ArtifactStatus.READY, run_id="run-1", created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_link_delivery_resolves_the_download_url_without_a_network_call() -> None:
    provider = LinkDeliveryProvider(base_url="https://analyst.example.com")

    result = await provider.send(artifact=_artifact(), destination="unused")

    assert result.success is True
    assert result.provider_metadata["link"] == "https://analyst.example.com/artifacts/artifact-1"


@pytest.mark.asyncio
async def test_link_delivery_strips_a_trailing_slash_from_the_base_url() -> None:
    provider = LinkDeliveryProvider(base_url="https://analyst.example.com/")

    result = await provider.send(artifact=_artifact(), destination="unused")

    assert result.provider_metadata["link"] == "https://analyst.example.com/artifacts/artifact-1"


@pytest.mark.asyncio
async def test_webhook_posts_artifact_metadata_and_a_link_never_the_bytes() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.content
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"received": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert result.success is True
    assert captured["url"] == "https://hooks.example.com/in"
    import json as _json
    payload = _json.loads(captured["json"])
    assert payload["artifact_id"] == "artifact-1"
    assert payload["link"] == "https://analyst.example.com/artifacts/artifact-1"
    assert "sha256" not in payload  # only what a receiver needs, nothing about the file's identity beyond that
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_5xx_is_retryable() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503, text="down")))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert result.success is False
    assert result.retryable is True
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_4xx_is_not_retryable() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404, text="not found")))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert result.success is False
    assert result.retryable is False


@pytest.mark.asyncio
async def test_webhook_response_body_is_truncated_and_stored_as_a_snippet() -> None:
    long_body = "x" * 5_000
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(500, text=long_body)))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert len(result.provider_metadata["response_snippet"]) <= 200
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_response_body_has_credential_looking_material_redacted() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(500, text="Bearer sk-abcdefghijklmnopqrstuvwx failed"),
    ))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert "sk-abcdefghijklmnopqrstuvwx" not in result.provider_metadata["response_snippet"]
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_never_stores_response_headers() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"Set-Cookie": "session=deadbeef"}, json={"ok": True}),
    ))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert "headers" not in result.provider_metadata
    assert "deadbeef" not in str(result.provider_metadata)
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_timeout_is_reported_as_a_retryable_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = WebhookDeliveryProvider(client=client, base_url="https://analyst.example.com", timeout_seconds=5)

    result = await provider.send(artifact=_artifact(), destination="https://hooks.example.com/in")

    assert result.success is False
    assert result.retryable is True
