"""Execute a saved report definition: resolve, rerun, compile, preview or publish.

This module never imports anything from ``app.llm`` and never will --
`tests/contracts/test_saved_report_boundaries.py` asserts it transitively.
"Saving or executing a report definition must not call an LLM" is enforced
here structurally, not just by a runtime check: a definition whose narrative
policy demands a new agent investigation is refused before anything else
runs, and refused by a different code path entirely (the API route calls the
existing agent-run machinery directly; this module has no way to reach it).

Steps 1-8 of an execution:

1. Resolve the relative period            -- ``app.reports.periods``
2. Compile semantic metric queries        -- ``compile_metric``, inside ``MetricRunner``
3. Validate them                          -- the same AST validator every query passes
4. Execute read-only                      -- ``AnalyticsSQLExecutor``
5. Mint new rerun evidence                -- ``ReportRerunService`` (fresh ``rerun_###`` ids)
6. Compile the canonical report           -- ``compile_report``
7. Preview or publish                     -- ``ReportPreview`` or rendered documents
8. Persist execution status and artifacts -- the caller, via ``SavedReportStore``

This module performs steps 1-7 and returns what step 8 needs to persist; it
does not touch ``SavedReportStore`` itself, so it stays testable without a
database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import uuid4

from app.analytics.presentation.assignment import assign_slots
from app.analytics.presentation.compiler import compile_report
from app.analytics.presentation.document_model import NarrativeStatus
from app.analytics.presentation.preview import ReportPreview, estimate_page_count, missing_required_content
from app.analytics.presentation.suitability import score_assignment
from app.analytics.presentation.templates import ReportTemplateError, ReportTemplateRegistry
from app.analytics.semantics.parameters import MetricParameters
from app.artifacts.contracts import Artifact
from app.artifacts.store import ArtifactStore
from app.contracts.actions import normalize_caveats
from app.environment.workspace import Workspace
from app.orchestration.publishing import DocumentFormat, ReportPublishingError, render_and_register_documents
from app.orchestration.reruns import ReportRerunError, ReportRerunService
from app.reports.contracts import SavedReportDefinition
from app.reports.periods import ResolvedPeriod, resolve_relative_period


class SavedReportExecutionError(Exception):
    """Raised when a saved report cannot be executed as asked."""


@dataclass(frozen=True, slots=True)
class SavedReportExecutionResult:
    """What one execution produced, before the caller persists it."""

    run_id: str
    resolved: ResolvedPeriod
    preview: ReportPreview | None
    artifacts: list[Artifact]


def _build_parameters(
    definition: SavedReportDefinition, period,
) -> list[MetricParameters]:
    return [
        MetricParameters(
            metric=item.metric, period=period, dimensions=item.dimensions,
            filters=item.filters, grain=item.grain,
        )
        for item in definition.metric_requests
    ]


def _narrative(definition: SavedReportDefinition) -> tuple[str, NarrativeStatus, str | None]:
    """The answer text, its freshness status, and the period it was written for."""

    if definition.narrative_policy == "include_original":
        return definition.seed_narrative or "", "pinned_to_original_period", definition.seed_narrative_period
    # "exclude" is the only other policy this module ever sees --
    # "require_new_investigation" is refused before this is called.
    return "", "excluded_from_refreshed_report", None


class SavedReportExecutionService:
    """Run a saved report definition once, deterministically."""

    def __init__(
        self, *, templates: ReportTemplateRegistry, reruns: ReportRerunService,
        workspace: Workspace, artifacts: ArtifactStore,
    ) -> None:
        self._templates = templates
        self._reruns = reruns
        self._workspace = workspace
        self._artifacts = artifacts

    async def execute(
        self, definition: SavedReportDefinition, *, mode: str,
        formats: list[DocumentFormat] | None = None, today: date | None = None,
    ) -> SavedReportExecutionResult:
        """Run steps 1-7. Raises ``SavedReportExecutionError`` on any failure.

        ``today`` is the UTC reference date the relative period resolves
        against; omitted, it is the real current UTC date. Tests pin it to
        exercise a specific boundary without waiting for the calendar.
        """

        if definition.narrative_policy == "require_new_investigation":
            raise SavedReportExecutionError(
                "This saved report requires a new agent investigation and cannot be executed "
                "deterministically. Start a new agent run instead."
            )
        try:
            template = self._templates.get(definition.template_id)
        except ReportTemplateError as error:
            raise SavedReportExecutionError(str(error)) from error

        resolved = resolve_relative_period(
            definition.default_period, today=today or datetime.now(timezone.utc).date(),
        )
        run_id = f"saved-report-{uuid4()}"
        parameters = _build_parameters(definition, resolved.period)

        try:
            outcomes = await self._reruns.run_all(run_id=run_id, requests=parameters)
        except ReportRerunError as error:
            raise SavedReportExecutionError(str(error)) from error

        charts = [outcome.chart for outcome in outcomes]
        sources = [outcome.source for outcome in outcomes]
        answer, narrative_status, analysis_period = _narrative(definition)

        assignment = assign_slots(template, charts, sources)
        content_order = assignment.content_order() if template.slots else None

        caveats = list(normalize_caveats([]))
        if template.version != definition.template_version:
            caveats = normalize_caveats([
                f"This report pinned {template.title} version {definition.template_version}, but the "
                f"current template is version {template.version}. It was compiled against the current "
                "version; update the saved report to pin it explicitly.",
            ])

        report = compile_report(
            template=template, run_id=run_id, answer=answer, charts=charts, sources=sources,
            generated_at=datetime.now(timezone.utc), period=resolved.period.describe(),
            title=definition.name, caveats=caveats, narrative_status=narrative_status,
            analysis_period=analysis_period, content_order=content_order,
        )

        if mode == "preview":
            suitability = score_assignment(assignment)
            preview = ReportPreview(
                template_name=template.name, template_title=template.title, report=report,
                suitability=suitability, assignment=assignment,
                missing_required_content=missing_required_content(template, assignment),
                estimated_page_count=estimate_page_count(report),
            )
            return SavedReportExecutionResult(run_id=run_id, resolved=resolved, preview=preview, artifacts=[])

        if mode != "publish":
            raise SavedReportExecutionError(f"Unknown execution mode: {mode!r}.")

        try:
            published = await render_and_register_documents(
                workspace_id=definition.workspace_id, report=report, charts=charts, template=template,
                run_id=run_id, formats=formats or ["pdf"], workspace=self._workspace, artifacts=self._artifacts,
                directory_name="saved-reports",
                extra_metadata={"saved_report_id": str(definition.id)},
            )
        except ReportPublishingError as error:
            raise SavedReportExecutionError(str(error)) from error

        return SavedReportExecutionResult(run_id=run_id, resolved=resolved, preview=None, artifacts=published)
