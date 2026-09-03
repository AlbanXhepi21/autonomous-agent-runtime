"""Cryptographically secure, single-use-grade tokens for sessions and recovery/verification.

Tokens are 256 bits of ``secrets``-module randomness; only their SHA-256
digest is ever persisted (in ``sessions``/``identity_tokens``), so a database
read alone cannot reconstruct a usable token. This is standard practice for
high-entropy random tokens -- unlike a password, a token has no guessable
structure for a hash to protect against, so no per-token salt or slow KDF is
needed here (that machinery is reserved for passwords; see
``app.identity.passwords``).
"""

from __future__ import annotations

import hashlib
import secrets

#: 256 bits -- comfortably infeasible to guess or enumerate.
TOKEN_BYTES = 32


def generate_token() -> str:
    """Return a new URL-safe random token. Never log or persist this value raw."""

    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the stable digest stored in place of the token itself."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
