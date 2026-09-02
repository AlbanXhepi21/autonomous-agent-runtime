"""Validation rules that keep a schedule's shape and timezone honest."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.scheduling.contracts import ScheduleConfig, ScheduledReportDefinition


def test_weekly_requires_day_of_week() -> None:
    with pytest.raises(ValidationError, match="requires 'day_of_week'"):
        ScheduleConfig(kind="weekly")


def test_day_of_week_is_rejected_outside_weekly() -> None:
    with pytest.raises(ValidationError, match="only meaningful for weekly"):
        ScheduleConfig(kind="daily", day_of_week=0)


def test_monthly_requires_day_of_month() -> None:
    with pytest.raises(ValidationError, match="requires 'day_of_month'"):
        ScheduleConfig(kind="monthly")


def test_day_of_month_is_capped_at_28() -> None:
    with pytest.raises(ValidationError):
        ScheduleConfig(kind="monthly", day_of_month=29)


def test_quarterly_requires_month_of_quarter_and_day_of_month() -> None:
    with pytest.raises(ValidationError, match="requires 'month_of_quarter'"):
        ScheduleConfig(kind="quarterly", day_of_month=1)


def test_month_of_quarter_is_rejected_outside_quarterly() -> None:
    with pytest.raises(ValidationError, match="only meaningful for quarterly"):
        ScheduleConfig(kind="monthly", day_of_month=1, month_of_quarter=1)


def test_a_valid_daily_config_round_trips() -> None:
    config = ScheduleConfig(kind="daily", hour=6, minute=30)

    assert config.hour == 6 and config.minute == 30


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ScheduleConfig.model_validate({"kind": "daily", "sql": "DROP TABLE scheduled_reports"})


def _definition(**overrides) -> ScheduledReportDefinition:
    now = datetime.now(UTC)
    fields = {
        "id": uuid4(), "saved_report_id": uuid4(), "workspace_id": "workspace-a",
        "schedule": ScheduleConfig(kind="daily", hour=6, minute=0), "timezone": "UTC",
        "formats": ["pdf"], "delivery_channel": None, "delivery_destination": None,
        "enabled": True, "next_run_at": now, "last_run_at": None, "last_result": None,
        "consecutive_failures": 0, "created_at": now, "updated_at": now,
    }
    fields.update(overrides)
    return ScheduledReportDefinition(**fields)


def test_an_unknown_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Unknown IANA timezone"):
        _definition(timezone="Mars/Olympus_Mons")


def test_a_known_iana_timezone_is_accepted() -> None:
    definition = _definition(timezone="America/New_York")

    assert definition.timezone == "America/New_York"


def test_delivery_channel_without_a_destination_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must be set together"):
        _definition(delivery_channel="webhook", delivery_destination=None)


def test_delivery_destination_without_a_channel_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must be set together"):
        _definition(delivery_channel=None, delivery_destination="https://example.com/hook")


def test_delivery_channel_and_destination_together_is_valid() -> None:
    definition = _definition(delivery_channel="webhook", delivery_destination="https://example.com/hook")

    assert definition.delivery_channel == "webhook"


def test_a_definition_is_frozen() -> None:
    definition = _definition()

    with pytest.raises(ValidationError):
        definition.enabled = False  # type: ignore[misc]
