"""SSRF guard, SSL mode enforcement, and DSN construction -- no network needed."""

import pytest

from app.datasources.contracts import DataSourceConnectionConfig
from app.datasources.security import (
    ConnectionSecurityError,
    assert_safe_host,
    assert_safe_ssl_mode,
    build_dsn,
    build_ssl_context,
)


@pytest.mark.parametrize("mode", ["disable", "allow", "prefer"])
def test_unsafe_ssl_modes_are_refused(mode: str) -> None:
    with pytest.raises(ConnectionSecurityError):
        assert_safe_ssl_mode(mode)


@pytest.mark.parametrize("mode", ["require", "verify-ca", "verify-full"])
def test_safe_ssl_modes_are_accepted(mode: str) -> None:
    assert_safe_ssl_mode(mode)  # does not raise


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "10.0.0.5", "172.16.0.1", "192.168.1.1", "169.254.169.254", "0.0.0.0"])
def test_private_and_reserved_hosts_are_refused(host: str) -> None:
    with pytest.raises(ConnectionSecurityError, match="private or reserved"):
        assert_safe_host(host)


def test_the_cloud_metadata_endpoint_is_refused() -> None:
    """169.254.169.254 -- the address every major cloud's instance metadata service uses."""

    with pytest.raises(ConnectionSecurityError):
        assert_safe_host("169.254.169.254")


def test_a_public_hostname_is_accepted() -> None:
    assert_safe_host("example.com")  # does not raise -- resolves publicly


def test_allow_local_bypasses_the_check() -> None:
    assert_safe_host("localhost", allow_local=True)  # does not raise


def test_an_unresolvable_host_is_refused() -> None:
    with pytest.raises(ConnectionSecurityError, match="could not be resolved"):
        assert_safe_host("this-host-does-not-exist.invalid")


def test_build_ssl_context_require_disables_verification() -> None:
    context = build_ssl_context("require")
    assert context.check_hostname is False


def test_build_ssl_context_verify_ca_checks_the_chain_but_not_hostname() -> None:
    context = build_ssl_context("verify-ca")
    assert context.check_hostname is False


def test_build_ssl_context_verify_full_checks_everything() -> None:
    context = build_ssl_context("verify-full")
    assert context.check_hostname is True


def test_build_dsn_percent_encodes_special_characters() -> None:
    config = DataSourceConnectionConfig(
        host="db.example.com", database="analytics", username="ro user", allowed_schemas=["public"],
    )
    dsn = build_dsn(config, "p@ss:word/weird")

    assert "p@ss:word/weird" not in dsn
    assert dsn.startswith("postgresql+asyncpg://")
    assert "db.example.com:5432/analytics" in dsn


def test_build_dsn_registers_the_password_for_log_redaction() -> None:
    from app.core.logging import redact_secret_text

    config = DataSourceConnectionConfig(host="db.example.com", database="analytics", username="ro", allowed_schemas=["public"])
    build_dsn(config, "a-unique-marker-password-xyz123")

    assert redact_secret_text("leaked: a-unique-marker-password-xyz123") == "leaked: [REDACTED]"
