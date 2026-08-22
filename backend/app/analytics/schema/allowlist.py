"""Allow-list policy for the external analytics schema."""

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

    def permits(self, schema: str) -> bool:
        return schema in self.allowed_schemas
