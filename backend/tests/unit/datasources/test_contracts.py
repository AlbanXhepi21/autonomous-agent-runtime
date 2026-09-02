"""Validation rules that keep a data source's configuration and catalog honest."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.datasources.contracts import (
    DataSourceColumnCatalogEntry,
    DataSourceConnectionConfig,
    DataSourceRelationship,
)


def test_unsafe_ssl_modes_are_rejected_by_the_type_itself() -> None:
    with pytest.raises(ValidationError):
        DataSourceConnectionConfig(host="db.example.com", database="analytics", username="ro", allowed_schemas=["public"], ssl_mode="disable")


def test_safe_ssl_modes_are_accepted() -> None:
    for mode in ("require", "verify-ca", "verify-full"):
        config = DataSourceConnectionConfig(host="db.example.com", database="analytics", username="ro", allowed_schemas=["public"], ssl_mode=mode)
        assert config.ssl_mode == mode


def test_at_least_one_schema_is_required() -> None:
    with pytest.raises(ValidationError):
        DataSourceConnectionConfig(host="db.example.com", database="analytics", username="ro", allowed_schemas=[])


def test_a_schema_may_be_listed_only_once() -> None:
    with pytest.raises(ValidationError, match="only once"):
        DataSourceConnectionConfig(host="db.example.com", database="analytics", username="ro", allowed_schemas=["public", "public"])


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DataSourceConnectionConfig.model_validate({
            "host": "db.example.com", "database": "analytics", "username": "ro", "allowed_schemas": ["public"],
            "password": "should-not-be-here",
        })


def test_a_sensitive_column_cannot_carry_example_values() -> None:
    with pytest.raises(ValidationError, match="must not carry sampled example values"):
        DataSourceColumnCatalogEntry(
            id=uuid4(), table_id=uuid4(), technical_name="email", data_type="text",
            sensitivity="personal_data", example_values=["a@example.com"],
        )


def test_a_non_sensitive_column_can_carry_example_values() -> None:
    column = DataSourceColumnCatalogEntry(
        id=uuid4(), table_id=uuid4(), technical_name="status", data_type="text",
        sensitivity="internal", example_values=["active", "archived"],
    )
    assert column.example_values == ["active", "archived"]


@pytest.mark.parametrize("sensitivity", ["personal_data", "financial_data", "authentication_secret", "restricted"])
def test_every_sensitive_classification_blocks_example_values(sensitivity: str) -> None:
    with pytest.raises(ValidationError):
        DataSourceColumnCatalogEntry(
            id=uuid4(), table_id=uuid4(), technical_name="x", data_type="text",
            sensitivity=sensitivity, example_values=["value"],
        )


def _relationship(**overrides) -> DataSourceRelationship:
    now = datetime.now(timezone.utc)
    fields = dict(
        id=uuid4(), data_source_id=uuid4(), source_table="orders", source_column="customer_id",
        target_table="customers", target_column="id", cardinality="many_to_one", confidence=1.0,
        discovery_method="foreign_key", approval_status="pending", approved_by=None, approved_at=None,
        created_at=now, updated_at=now,
    )
    fields.update(overrides)
    return DataSourceRelationship(**fields)


def test_a_relationship_defaults_to_pending_approval() -> None:
    relationship = _relationship()
    assert relationship.approval_status == "pending"


def test_confidence_is_bounded_zero_to_one() -> None:
    with pytest.raises(ValidationError):
        _relationship(confidence=1.5)
    with pytest.raises(ValidationError):
        _relationship(confidence=-0.1)


def test_a_relationship_is_frozen() -> None:
    relationship = _relationship()
    with pytest.raises(ValidationError):
        relationship.approval_status = "approved"  # type: ignore[misc]
