"""`update_investigation_plan` validates structure only; it trusts no status claim."""

import pytest

from app.tools.execution import ToolExecutor
from app.tools.planning import UpdateInvestigationPlanTool
from app.tools.registry import ToolRegistry


def plan_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "objective": "Understand payment failures in 2026",
        "request_class": "executive_report",
        "questions": [
            {"id": "q1", "question": "What is the total failure volume?", "status": "pending", "evidence_ids": []},
        ],
        "outputs": [
            {"id": "o1", "kind": "kpi", "purpose": "Total failures", "required": True, "status": "pending", "display_id": None},
        ],
        "completion_criteria": ["State the total volume with evidence."],
        "maximum_displays": 4,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_a_valid_plan_is_accepted_and_echoed_back() -> None:
    registry = ToolRegistry()
    registry.register(UpdateInvestigationPlanTool())

    result = await ToolExecutor(registry).execute("update_investigation_plan", {"plan": plan_payload()})

    assert result.success
    assert result.output["plan"]["request_class"] == "executive_report"
    assert result.output["plan"]["questions"][0]["id"] == "q1"


@pytest.mark.asyncio
async def test_an_unknown_field_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(UpdateInvestigationPlanTool())

    result = await ToolExecutor(registry).execute(
        "update_investigation_plan", {"plan": plan_payload(unexpected_field=True)}
    )

    assert not result.success
    assert result.metadata["failure_category"] == "tool_validation_error"


@pytest.mark.asyncio
async def test_an_out_of_range_display_budget_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(UpdateInvestigationPlanTool())

    result = await ToolExecutor(registry).execute(
        "update_investigation_plan", {"plan": plan_payload(maximum_displays=20)}
    )

    assert not result.success


@pytest.mark.asyncio
async def test_duplicate_question_ids_are_rejected() -> None:
    registry = ToolRegistry()
    registry.register(UpdateInvestigationPlanTool())
    payload = plan_payload(questions=[
        {"id": "q1", "question": "A?", "status": "pending", "evidence_ids": []},
        {"id": "q1", "question": "B?", "status": "pending", "evidence_ids": []},
    ])

    result = await ToolExecutor(registry).execute("update_investigation_plan", {"plan": payload})

    assert not result.success
