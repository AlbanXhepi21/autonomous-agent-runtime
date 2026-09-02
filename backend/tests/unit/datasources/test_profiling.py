"""Classification suggestions -- pure logic, no database.

Live table profiling, sampling, and relationship discovery against a real
database are covered in tests/integration/test_datasource_profiling.py; this
file is only the deterministic name/type heuristics.
"""

import pytest

from app.datasources.profiling import suggest_role, suggest_sensitivity


@pytest.mark.parametrize(
    "column_name, expected",
    [
        ("password", "authentication_secret"),
        ("password_hash", "authentication_secret"),
        ("api_key", "authentication_secret"),
        ("secret_token", "authentication_secret"),
        ("ssn", "restricted"),
        ("social_security_number", "restricted"),
        ("credit_card_number", "financial_data"),
        ("iban", "financial_data"),
        ("salary", "financial_data"),
        ("customer_email", "personal_data"),
        ("phone_number", "personal_data"),
        ("home_address", "personal_data"),
        ("title", "internal"),
        ("status", "internal"),
        ("id", "internal"),
    ],
)
def test_suggest_sensitivity(column_name: str, expected: str) -> None:
    assert suggest_sensitivity(column_name) == expected


def test_a_primary_key_is_suggested_as_primary_key_regardless_of_name() -> None:
    assert suggest_role(name="whatever", data_type="uuid", primary_key=True, foreign_key_target=None) == "primary_key"


def test_a_foreign_key_is_suggested_as_identifier() -> None:
    assert suggest_role(name="owner", data_type="uuid", primary_key=False, foreign_key_target="users.id") == "identifier"


@pytest.mark.parametrize("name", ["created_at", "updated_at", "start_date", "event_time"])
def test_a_time_like_name_is_suggested_as_time(name: str) -> None:
    assert suggest_role(name=name, data_type="timestamp", primary_key=False, foreign_key_target=None) == "time"


def test_an_id_suffixed_column_is_suggested_as_identifier_not_measure() -> None:
    """A numeric-looking _id column (e.g. a bigint surrogate FK) is not a measure."""

    assert suggest_role(name="customer_id", data_type="bigint", primary_key=False, foreign_key_target=None) == "identifier"


def test_a_numeric_column_is_suggested_as_a_measure() -> None:
    assert suggest_role(name="total_amount", data_type="numeric", primary_key=False, foreign_key_target=None) == "measure"


def test_a_text_column_is_suggested_as_a_dimension() -> None:
    assert suggest_role(name="status", data_type="text", primary_key=False, foreign_key_target=None) == "dimension"
