"""Allow-list policy for the external analytics schema."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyticsSchemaPolicy:
    allowed_schemas: frozenset[str]

    @classmethod
    def configured(cls, schema: str) -> "AnalyticsSchemaPolicy":
        cleaned = schema.strip()
        if not cleaned:
            raise ValueError("Analytics schema must not be blank.")
        return cls(frozenset({cleaned}))

    @classmethod
    def for_schemas(cls, schemas: Iterable[str]) -> "AnalyticsSchemaPolicy":
        """A policy over several schemas -- a workspace data source's own allowlist.

        Unlike ``configured``, which exists for the single process-wide
        ``ANALYTICS_DB_SCHEMA`` setting, a workspace connection may approve
        more than one schema at onboarding time.
        """

        cleaned = frozenset(schema.strip() for schema in schemas if schema.strip())
        if not cleaned:
            raise ValueError("At least one analytics schema must be allowed.")
        return cls(cleaned)

    def permits(self, schema: str) -> bool:
        return schema in self.allowed_schemas
