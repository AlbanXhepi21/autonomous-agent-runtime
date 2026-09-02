"""Envelope encryption for a workspace-supplied data source password.

Nothing else in this codebase stores a dynamic, caller-supplied secret at
rest -- ``CredentialProvider`` (``app.security.credentials``) resolves a
fixed logical name to an environment variable, which is exactly wrong for
"a workspace typed a password into an onboarding form." This module is the
new plumbing that case actually needs: one master key, resolved through the
existing ``CredentialProvider`` exactly like any other secret, encrypting
many rows.

Losing or rotating the master key makes every stored password unrecoverable
-- there is no key history. Rotation therefore means re-onboarding every
connection, not a transparent re-encryption; that trade-off is deliberate for
a first version rather than building key-versioning nobody has asked for yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cryptography.fernet import Fernet, InvalidToken

from app.security.credentials import CredentialProvider, SecretReference

ENCRYPTION_KEY_REFERENCE = SecretReference(name="datasource_encryption.default")


class SecretCipherError(Exception):
    """Raised when a secret cannot be encrypted or decrypted as asked."""


class SecretCipher(ABC):
    """Encrypt and decrypt one secret at a time, at rest."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Return an opaque, storable ciphertext. Never logged, never returned by an API."""

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Return the original plaintext, or raise SecretCipherError."""


class FernetSecretCipher(SecretCipher):
    """AES-128-CBC + HMAC (via Fernet), keyed by the configured master key.

    The master key itself is resolved through the existing
    ``CredentialProvider`` -- reusing that seam means a data source password
    gets the same defensive log redaction (``register_secret_value``) as
    every other secret in this application the moment the key is resolved.
    """

    def __init__(self, credentials: CredentialProvider) -> None:
        key = credentials.resolve(ENCRYPTION_KEY_REFERENCE)
        if not key:
            raise SecretCipherError(
                "DATA_SOURCE_ENCRYPTION_KEY is not configured; a workspace data source "
                "cannot be saved until it is set."
            )
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, TypeError) as error:
            raise SecretCipherError("DATA_SOURCE_ENCRYPTION_KEY is not a valid Fernet key.") from error

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as error:
            raise SecretCipherError("Stored data source credential could not be decrypted.") from error
