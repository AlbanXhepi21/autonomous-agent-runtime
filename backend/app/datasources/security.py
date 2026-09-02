"""Guards a workspace-supplied connection must pass before a socket ever opens.

Three independent controls, each refusing before any network call:
unsafe SSL modes, a host resolving into a private/internal network (SSRF),
and the password ever reaching a log line. None of these depend on the
target database cooperating -- they run against the configuration alone, or
against DNS resolution the caller cannot influence once it's resolved.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl as ssl_module
from urllib.parse import quote

from app.core.logging import register_secret_value
from app.datasources.contracts import DataSourceConnectionConfig, SSLMode

#: "disable" and "allow" permit a silent unencrypted connection; "prefer"
#: silently downgrades to unencrypted the moment the server doesn't offer
#: TLS. All three are refused outright rather than merely defaulted away
#: from -- an onboarding form cannot accidentally select an unsafe mode.
_UNSAFE_SSL_MODES = frozenset({"disable", "allow", "prefer"})


class ConnectionSecurityError(Exception):
    """Raised when a connection configuration fails a security check."""


def assert_safe_ssl_mode(ssl_mode: str) -> None:
    if ssl_mode in _UNSAFE_SSL_MODES:
        raise ConnectionSecurityError(
            f"SSL mode {ssl_mode!r} permits an unencrypted or unverified connection and is refused. "
            "Use 'require', 'verify-ca', or 'verify-full'."
        )


def assert_safe_host(host: str, *, allow_local: bool = False) -> None:
    """Refuse a host that resolves to a private, loopback, or link-local address.

    Resolved immediately before use rather than cached, so a host that starts
    pointing internally sometime after onboarding (DNS rebinding, or a record
    an operator changes later) is caught the next time a connection actually
    opens, not just once at setup. This is DNS-resolution-time protection,
    not connect-time pinning: a sufficiently adversarial DNS server could
    still race a re-resolution between this check and the driver's own
    connect -- acceptable for a workspace-supplied analytics source an
    operator explicitly configured, not a hardened multi-tenant SSRF barrier.
    """

    if allow_local:
        return
    try:
        resolved = socket.getaddrinfo(host, None)
    except socket.gaierror as error:
        raise ConnectionSecurityError(f"Host {host!r} could not be resolved.") from error
    for info in resolved:
        raw_address = info[4][0].split("%")[0]  # strip an IPv6 zone id, e.g. "fe80::1%eth0"
        address = ipaddress.ip_address(raw_address)
        if (
            address.is_private or address.is_loopback or address.is_link_local
            or address.is_reserved or address.is_multicast or address.is_unspecified
        ):
            raise ConnectionSecurityError(
                f"Host {host!r} resolves to {address}, a private or reserved address. "
                "A workspace data source may only connect to a publicly routable database."
            )


def build_ssl_context(ssl_mode: SSLMode) -> ssl_module.SSLContext:
    """Map a libpq-style sslmode onto a stdlib SSL context.

    Verification is always against the system trust store -- there is no
    per-connection custom CA upload in this version, so "verify-ca" and
    "verify-full" both require the target's certificate to chain to a CA
    this process already trusts.
    """

    context = ssl_module.create_default_context()
    if ssl_mode == "require":
        context.check_hostname = False
        context.verify_mode = ssl_module.CERT_NONE
    elif ssl_mode == "verify-ca":
        context.check_hostname = False
    # "verify-full" keeps the default context's hostname + chain verification.
    return context


def build_dsn(config: DataSourceConnectionConfig, password: str) -> str:
    """Build a connection URL. The password is registered for log redaction
    the instant it is used, so any accidental echo downstream is caught --
    defense in depth, not a substitute for never logging the URL itself.
    """

    register_secret_value(password)
    user = quote(config.username, safe="")
    secret = quote(password, safe="")
    host = quote(config.host, safe="")
    database = quote(config.database, safe="")
    return f"postgresql+asyncpg://{user}:{secret}@{host}:{config.port}/{database}"
