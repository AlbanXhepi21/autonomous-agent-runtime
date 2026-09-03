"""Argon2id password hashing.

``argon2-cffi`` is the reference Python binding for the Argon2 reference
implementation and defaults to the Argon2id variant, the profile OWASP
recommends for password storage. Nothing here re-derives or configures the
underlying KDF -- this module is a thin, typed wrapper, not a new
implementation of anything cryptographic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from argon2 import PasswordHasher as _Argon2PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError


class PasswordHasher(ABC):
    """Hash and verify passwords without exposing the algorithm to callers."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Return an encoded hash safe to store; never the password itself."""

    @abstractmethod
    def verify(self, *, password_hash: str, password: str) -> bool:
        """Return whether ``password`` matches ``password_hash``, never raising."""

    @abstractmethod
    def needs_rehash(self, password_hash: str) -> bool:
        """Return whether a hash was produced with parameters weaker than current defaults."""


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._hasher = _Argon2PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, *, password_hash: str, password: str) -> bool:
        try:
            self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False
        return True

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHash:
            return False
