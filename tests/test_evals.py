"""V7.2 deterministic evaluation framework coverage."""

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evals.contracts import EvalCase, EvalDataset
from app.evals.runner import EvalRunner, load_dataset, load_datasets
from app.evals.reports import format_report


DATASETS = Path(__file__).parents[1] / "app" / "evals" / "datasets"


def case(**updates: object) -> EvalCase:
    values = {"id": "test.case", "name": "Test", "description": "A test case.", "goal": "Finish."}
    values.update(updates)
    return EvalCase.model_validate(values)


def test_dataset_parsing_and_invalid_case_validation(tmp_path: Path) -> None:
    dataset = load_dataset(DATASETS / "basic.json")
    assert dataset.suite == "basic" and len(dataset.cases) == 3
    with pytest.raises(ValidationError):
        EvalCase(id="", name="Test", description="Description", goal="Goal")
    with pytest.raises(ValidationError):
        EvalDataset(suite="duplicate", cases=[case(), case()])


@pytest.mark.asyncio
async def test_single_case_pass_fail_and_trace_reference() -> None:
    dataset = load_dataset(DATASETS / "basic.json")
    result = await EvalRunner().run_case(dataset.cases[0], suite=dataset.suite)
    assert result.passed and result.run_id == result.trace_run_id

    failing = case(expected_capabilities=["missing_tool"], setup={"actions": [
        {"action_type": "finish", "reasoning_summary": "", "final_answer": "Done."}]})
    failed = await EvalRunner().run_case(failing)
    assert not failed.passed and "Required tools not used" in failed.failure_reasons[0]


@pytest.mark.asyncio
async def test_suite_evaluators_and_repeatability() -> None:
    datasets = load_datasets(DATASETS)
    skills = await EvalRunner().run_suite(datasets["skills"])
    assert all(result.passed for result in skills.results)

    basic = datasets["basic"]
    first, second = await asyncio.gather(EvalRunner().run_suite(basic), EvalRunner().run_suite(basic))
    assert [item.passed for item in first.results] == [item.passed for item in second.results] == [True, True, True]


@pytest.mark.asyncio
async def test_forbidden_tool_and_delegation_evaluators() -> None:
    tools = load_dataset(DATASETS / "tools.json")
    forbidden = case(forbidden_capabilities=["calculator"], setup=tools.cases[0].setup)
    result = await EvalRunner().run_case(forbidden)
    assert not result.passed and any("Forbidden tools used" in reason for reason in result.failure_reasons)

    delegation = load_dataset(DATASETS / "delegation.json")
    result = await EvalRunner().run_case(delegation.cases[0], suite="delegation")
    assert result.passed


@pytest.mark.asyncio
async def test_report_aggregation() -> None:
    report = await EvalRunner().run_suite(load_dataset(DATASETS / "basic.json"))
    rendered = format_report(report)
    assert report.total == 3 and report.passed == 3 and report.pass_rate == 1
    assert "Suite: basic" in rendered and "3 passed" in rendered and "Average LLM calls" in rendered
