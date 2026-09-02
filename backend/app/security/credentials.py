"""Runtime-only credential references, environment resolution, and detection helpers."""

import os
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.logging import register_secret_value

_REFERENCE = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+$")
_SECRET_PATTERNS = (
    re.compile(r"\b(?:ghp|github_pat|sk|AIza)[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}\b", re.I),
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"://[^\s/:]+:[^\s@]+@"),
    re.compile(r"\b(?:api[_-]?key|password|secret|token)\s*[=:]\s*[^\s,;]+", re.I),
)


class SecretReference(BaseModel):
    """A logical identity supplied to trusted integrations, never a raw secret."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=3, max_length=128)

    @field_validator("name")
    @classmethod
    def logical_name_only(cls, value: str) -> str:
        if not _REFERENCE.fullmatch(value):
            raise ValueError("Secret references must be logical dotted names.")
        return value


class CredentialProvider(ABC):
    """Resolve a runtime-owned reference for a trusted integration only."""

    @abstractmethod
    def resolve(self, reference: SecretReference) -> str | None:
        """Return a raw secret internally, or None when not configured."""


class EnvironmentCredentialProvider(CredentialProvider):
    """Map fixed logical references to environment variables at runtime startup."""

    DEFAULT_REFERENCES = {
        "openai.default": "OPENAI_API_KEY",
        "database.default": "DATABASE_URL",
        "github.default": "GITHUB_TOKEN",
        "smtp.default": "SMTP_PASSWORD",
        "datasource_encryption.default": "DATA_SOURCE_ENCRYPTION_KEY",
    }

    def __init__(self, references: dict[str, str] | None = None) -> None:
        self._references = dict(references or self.DEFAULT_REFERENCES)

    def resolve(self, reference: SecretReference) -> str | None:
        environment_name = self._references.get(reference.name)
        value = os.environ.get(environment_name, "") if environment_name else ""
        if value:
            register_secret_value(value)
            return value
        return None


class SecretRedactor:
    """Conservative string redaction for known values and obvious credential material."""

    def __init__(self, known_values: tuple[str, ...] = ()) -> None:
        self._known_values = tuple(value for value in known_values if value)

    def redact(self, value: str) -> str:
        redacted = value
        for secret in self._known_values:
            redacted = redacted.replace(secret, "[REDACTED]")
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted


def contains_secret_material(value: str) -> bool:
    """Detect common credential forms for storage/artifact rejection, not validation."""

    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
