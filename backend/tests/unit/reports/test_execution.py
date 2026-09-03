"""Executing a saved report definition: resolve, rerun, compile, preview or publish.

The rerun step is faked here rather than hitting the real analytics database --
what this module is responsible for is everything *around* a rerun (period
resolution, narrative policy, template pinning, preview vs. publish), not the
rerun itself, which ``ReportRerunService`` already owns and already has its
own tests. The fake stands in exactly at that seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.analytics.presentation.charts import ChartSpec, KPIItem
from app.analytics.presentation.templates import ReportTemplateRegistry
from app.analytics.semantics.parameters import MetricParameters
from app.artifacts.store import WorkspaceArtifactStore
from app.contracts.answers import AnswerSource
from app.environment.workspace import Workspace
from app.orchestration.reruns import RerunOutcome
from app.reports.contracts import RelativePeriod, SavedMetricRequest, SavedReportDefinition
from app.reports.execution import SavedReportExecutionError, SavedReportExecutionService


@dataclass(frozen=True, slots=True)
class _FakeRerunService:
    """Hands back one canned KPI outcome per requested metric, in order."""

    calls: list[tuple[str, list[MetricParameters]]]

    async def run_all(self, *, run_id: str, requests: list[MetricParameters]) -> list[RerunOutcome]:
        self.calls.append((run_id, list(requests)))
        outcomes = []
        for index, parameters in enumerate(requests, start=1):
            query_id = f"rerun_{index:03d}"
            chart = ChartSpec(
                id=f"{query_id}-kpi", type="kpi", title=f"{parameters.metric} · {parameters.period.describe()}",
                source_query_ids=[query_id],
                kpis=[KPIItem(label=parameters.metric.capitalize(), value="42", raw_value=42,
                              source_column=parameters.metric, source_query_id=query_id)],
            )
            source = AnswerSource(id=query_id, kind="metric_rerun", run_id=run_id,
                                  label=parameters.metric, metric=parameters.metric)
            outcomes.append(RerunOutcome(result=None, source=source, chart=chart))  # type: ignore[arg-type]
        return outcomes


def _definition(**overrides) -> SavedReportDefinition:
    now = datetime.now(UTC)
    fields = {
        "id": uuid4(), "workspace_id": uuid4(), "owner": None, "name": "Weekly Revenue",
        "description": None, "template_id": "analysis_summary", "template_version": "4",
        "metric_requests": [SavedMetricRequest(metric="revenue"), SavedMetricRequest(metric="orders")],
        "default_period": RelativePeriod(kind="last_n_days", days=7),
        "narrative_policy": "exclude", "seed_run_id": None, "seed_narrative": None,
        "seed_narrative_period": None, "version": 1, "status": "active",
        "created_at": now, "updated_at": now,
    }
    fields.update(overrides)
    return SavedReportDefinition(**fields)


def _service(tmp_path, reruns: _FakeRerunService | None = None) -> SavedReportExecutionService:
    workspace = Workspace(tmp_path)
    return SavedReportExecutionService(
        templates=ReportTemplateRegistry(), reruns=reruns or _FakeRerunService(calls=[]),
        workspace=workspace, artifacts=WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760),
    )


@pytest.mark.asyncio
async def test_preview_compiles_without_writing_a_file(tmp_path) -> None:
    result = await _service(tmp_path).execute(_definition(), mode="preview", today=date(2026, 1, 15))

    assert result.preview is not None
    assert result.artifacts == []
    assert result.resolved.period.start == date(2026, 1, 8)
    assert result.resolved.period.end == date(2026, 1, 15)


@pytest.mark.asyncio
async def test_publish_writes_a_real_document(tmp_path) -> None:
    result = await _service(tmp_path).execute(
        _definition(), mode="publish", formats=["pdf"], today=date(2026, 1, 15),
    )

    assert result.preview is None
    assert len(result.artifacts) == 1
    assert result.artifacts[0].media_type == "application/pdf"
    assert result.artifacts[0].size > 1_000


@pytest.mark.asyncio
async def test_each_execution_mints_a_fresh_run_id(tmp_path) -> None:
    service = _service(tmp_path)
    definition = _definition()

    first = await service.execute(definition, mode="preview", today=date(2026, 1, 15))
    second = await service.execute(definition, mode="preview", today=date(2026, 1, 15))

    assert first.run_id != second.run_id


@pytest.mark.asyncio
async def test_the_resolved_period_is_passed_through_to_every_metric_request(tmp_path) -> None:
    reruns = _FakeRerunService(calls=[])

    await _service(tmp_path, reruns).execute(_definition(), mode="preview", today=date(2026, 1, 15))

    ((_, requests),) = reruns.calls
    assert len(requests) == 2
    assert {item.metric for item in requests} == {"revenue", "orders"}
    assert all(item.period.start == date(2026, 1, 8) and item.period.end == date(2026, 1, 15) for item in requests)


@pytest.mark.asyncio
async def test_require_new_investigation_is_refused_before_anything_runs(tmp_path) -> None:
    reruns = _FakeRerunService(calls=[])
    definition = _definition(narrative_policy="require_new_investigation")

    with pytest.raises(SavedReportExecutionError, match="new agent investigation"):
        await _service(tmp_path, reruns).execute(definition, mode="preview")

    # Refused before the rerun step, not after -- no query was even attempted.
    assert reruns.calls == []


@pytest.mark.asyncio
async def test_an_unknown_template_is_refused_with_a_clear_error(tmp_path) -> None:
    definition = _definition(template_id="not_a_real_template")

    with pytest.raises(SavedReportExecutionError, match="not_a_real_template"):
        await _service(tmp_path).execute(definition, mode="preview")


@pytest.mark.asyncio
async def test_an_unknown_mode_is_refused(tmp_path) -> None:
    with pytest.raises(SavedReportExecutionError, match="Unknown execution mode"):
        await _service(tmp_path).execute(_definition(), mode="rerun_everything")


@pytest.mark.asyncio
async def test_a_stale_template_pin_is_surfaced_as_a_caveat_not_a_failure(tmp_path) -> None:
    # The registry's analysis_summary is version "4"; pin it to a version that
    # is no longer current and confirm execution still succeeds.
    definition = _definition(template_version="1")

    result = await _service(tmp_path).execute(definition, mode="preview", today=date(2026, 1, 15))

    assert result.preview is not None
    caveats = [block.stated for block in result.preview.report.blocks_of("caveats")]
    flattened = [line for group in caveats for line in group]
    assert any("version 1" in line and "version 4" in line for line in flattened)


@pytest.mark.asyncio
async def test_include_original_reuses_the_seed_narrative_with_a_pinned_status(tmp_path) -> None:
    definition = _definition(
        narrative_policy="include_original", seed_narrative="Revenue grew 18% in the seed period.",
        seed_narrative_period="August 2026",
    )

    result = await _service(tmp_path).execute(definition, mode="preview", today=date(2026, 1, 15))

    report = result.preview.report
    assert report.narrative_period_status == "pinned_to_original_period"
    narrative_text = "\n".join(
        line.text for block in report.blocks_of("narrative") for line in block.lines
    )
    assert "Revenue grew 18%" in narrative_text


@pytest.mark.asyncio
async def test_exclude_never_carries_narrative_prose(tmp_path) -> None:
    result = await _service(tmp_path).execute(_definition(narrative_policy="exclude"), mode="preview")

    report = result.preview.report
    assert report.narrative_period_status == "excluded_from_refreshed_report"
    assert all(not block.lines for block in report.blocks_of("narrative"))
