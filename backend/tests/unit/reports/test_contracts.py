"""Validation rules that keep a saved report's JSONB columns honest.

Every column stored as JSONB round-trips through one of these Pydantic
contracts rather than being read or written as a raw dict, so a malformed
row can never be written in the first place.
"""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.reports.contracts import RelativePeriod, SavedMetricRequest, SavedReportDefinition


def _definition(**overrides) -> SavedReportDefinition:
    now = datetime.now(UTC)
    fields = {
        "id": uuid4(), "workspace_id": uuid4(), "owner": None, "name": "Weekly Revenue",
        "description": None, "template_id": "executive_dashboard", "template_version": "3",
        "metric_requests": [SavedMetricRequest(metric="revenue")],
        "default_period": RelativePeriod(kind="last_n_days", days=7),
        "narrative_policy": "exclude", "seed_run_id": None, "seed_narrative": None,
        "seed_narrative_period": None, "version": 1, "status": "active",
        "created_at": now, "updated_at": now,
    }
    fields.update(overrides)
    return SavedReportDefinition(**fields)


# -- RelativePeriod: kind and shape must agree --------------------------------


def test_last_n_days_requires_days() -> None:
    with pytest.raises(ValidationError, match="requires 'days'"):
        RelativePeriod(kind="last_n_days")


def test_days_is_rejected_outside_last_n_days() -> None:
    with pytest.raises(ValidationError, match="only meaningful for last_n_days"):
        RelativePeriod(kind="current_month", days=7)


def test_fixed_requires_both_bounds() -> None:
    with pytest.raises(ValidationError, match="requires both"):
        RelativePeriod(kind="fixed", start=date(2026, 1, 1))


def test_fixed_end_must_be_after_start() -> None:
    with pytest.raises(ValidationError, match="end after it starts"):
        RelativePeriod(kind="fixed", start=date(2026, 4, 1), end=date(2026, 1, 1))


def test_start_and_end_are_rejected_outside_fixed() -> None:
    with pytest.raises(ValidationError, match="only meaningful for fixed"):
        RelativePeriod(kind="current_year", start=date(2026, 1, 1), end=date(2026, 4, 1))


def test_a_valid_fixed_period_round_trips() -> None:
    period = RelativePeriod(kind="fixed", start=date(2026, 1, 1), end=date(2026, 4, 1))

    assert period.start == date(2026, 1, 1) and period.end == date(2026, 4, 1)


# -- SavedMetricRequest --------------------------------------------------------


def test_a_dimension_may_be_requested_only_once() -> None:
    with pytest.raises(ValidationError, match="only once"):
        SavedMetricRequest(metric="revenue", dimensions=["country", "country"])


def test_at_most_three_dimensions() -> None:
    with pytest.raises(ValidationError):
        SavedMetricRequest(metric="revenue", dimensions=["country", "channel", "device", "campaign"])


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SavedMetricRequest.model_validate({"metric": "revenue", "sql": "DROP TABLE orders"})


# -- SavedReportDefinition -----------------------------------------------------


def test_include_original_requires_a_seed_narrative() -> None:
    with pytest.raises(ValidationError, match="requires a seed_narrative"):
        _definition(narrative_policy="include_original", seed_narrative=None)


def test_include_original_is_valid_with_a_seed_narrative() -> None:
    definition = _definition(
        narrative_policy="include_original", seed_narrative="Revenue grew 18%.",
        seed_narrative_period="August 2026",
    )

    assert definition.narrative_policy == "include_original"


def test_exclude_needs_no_seed_narrative() -> None:
    definition = _definition(narrative_policy="exclude")

    assert definition.seed_narrative is None


def test_at_least_one_metric_request_is_required() -> None:
    with pytest.raises(ValidationError):
        _definition(metric_requests=[])


def test_a_definition_is_frozen() -> None:
    definition = _definition()

    with pytest.raises(ValidationError):
        definition.name = "Renamed"  # type: ignore[misc]


def test_unknown_fields_are_rejected_on_a_definition() -> None:
    with pytest.raises(ValidationError):
        SavedReportDefinition.model_validate({**_definition().model_dump(), "factual_revenue": 163})
