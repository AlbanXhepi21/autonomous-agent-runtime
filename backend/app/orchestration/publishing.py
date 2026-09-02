"""Publish a stored run as a document.

Everything a report needs — the written answer, the displays, the evidence
registry — is already persisted with the run, so publishing is a deterministic
assembly rather than another agent turn. That keeps a re-export of the same run
byte-comparable in content, costs no tokens, and removes any chance of the
model quietly rewriting an analysis someone already signed off.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.analytics.presentation.assignment import TemplateAssignment, assign_slots
from app.analytics.presentation.charts import ChartSpec
from app.analytics.presentation.compiler import compile_report
from app.analytics.presentation.document_model import CompiledReport, NarrativeStatus
from app.analytics.presentation.documents import write_docx, write_pdf
from app.analytics.presentation.preview import (
    ReportPreview,
    TemplateSuitabilityOverview,
    estimate_page_count,
    missing_required_content,
)
from app.analytics.presentation.rasterize import render_chart_png
from app.analytics.presentation.suitability import recommend_template, score_assignment
from app.analytics.presentation.templates import (
    ReportTemplate,
    ReportTemplateError,
    ReportTemplateRegistry,
)
from app.analytics.semantics.parameters import MetricParameters
from app.artifacts.contracts import Artifact
from app.artifacts.store import ArtifactStore
from app.contracts.actions import normalize_caveats
from app.contracts.answers import AnswerSource
from app.conversations.store import ConversationStore
from app.core.logging import log_event
from app.environment.workspace import Workspace
from app.orchestration.reruns import ReportRerunError, ReportRerunService

DocumentFormat = Literal["pdf", "docx"]

_WRITERS = {"pdf": (write_pdf, "pdf", "application/pdf"),
            "docx": (write_docx, "docx",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

_logger = logging.getLogger(__name__)


class ReportPublishingError(Exception):
    """Raised when a run cannot be published as asked."""


def _period_label(metrics: list[MetricParameters]) -> str:
    """Name the period the recomputed figures describe.

    Taken from the requests themselves rather than from anything a caller typed,
    so the printed period cannot disagree with the data behind it.
    """

    described = list(dict.fromkeys(item.period.describe() for item in metrics))
    return described[0] if len(described) == 1 else "; ".join(described)


async def render_and_register_documents(
    *, report: CompiledReport, charts: list[ChartSpec], template: ReportTemplate, run_id: str,
    formats: list[DocumentFormat], workspace: Workspace, artifacts: ArtifactStore,
    directory_name: str = "published", extra_metadata: dict[str, object] | None = None,
) -> list[Artifact]:
    """Rasterize a compiled report's charts and write it in every requested format.

    The one place a compiled report becomes bytes on disk. ``ReportPublisher.publish``
    and saved-report execution both call this rather than each writing their own
    copy, so a published document is assembled identically regardless of what
    produced the report it prints.
    """

    directory = workspace.root / ".runtime" / directory_name / run_id
    # Drawn once from the compiled blocks, then shared by every renderer, so
    # the two formats cannot end up showing different pictures.
    drawn = {chart.id: chart for chart in charts}
    images = {
        block.chart_id: rendered
        for block in report.blocks_of("chart")
        if (source := drawn.get(block.chart_id)) is not None
        and (rendered := render_chart_png(
            source, directory / f"chart-{block.chart_id}.png", palette=template.theme.chart_palette,
        )) is not None
    }

    requested = [item for item in dict.fromkeys(formats) if template.supports(item)]
    if not requested:
        raise ReportPublishingError(
            f"The {template.title} template does not support the requested format."
        )

    published: list[Artifact] = []
    for document_format in requested:
        writer, suffix, media_type = _WRITERS[document_format]
        path = directory / f"{template.name}.{suffix}"
        try:
            writer(report, images, path, template.theme)
            artifact = await artifacts.register(
                run_id=run_id, source_path=path.relative_to(workspace.root).as_posix(),
                artifact_type="report_document", media_type=media_type,
                output_format=document_format, template_id=template.name,
                template_version=template.version,
                metadata={"template": template.name, "report_type": template.report_type.value,
                          "period": report.displayed_period or "", "chart_count": len(images),
                          "caveat_count": sum(len(block.stated) for block in report.blocks_of("caveats")),
                          "narrative_status": report.narrative_period_status,
                          "report_id": report.report_id,
                          "orientation": report.orientation,
                          "source_query_ids": report.cited_query_ids,
                          **(extra_metadata or {})},
            )
        except (OSError, ValueError) as error:
            raise ReportPublishingError("The report could not be written within configured limits.") from error
        published.append(artifact)
        log_event(_logger, logging.INFO, "report_published", run_id=run_id,
                  template=template.name, document_format=document_format,
                  chart_count=len(images), size=artifact.size)
    return published


@dataclass(frozen=True, slots=True)
class _ResolvedContent:
    """What one run contributes to a report, before a template lays it out.

    Built once and read by both ``preview`` and ``publish`` so the two can
    never see a different run than the other — the same charts, the same
    resolved evidence, the same period and narrative status either way.
    """

    charts: list[ChartSpec]
    sources: list[AnswerSource]
    caveats: list[str]
    answer: str
    period: str | None
    analysis_period: str | None
    narrative_status: NarrativeStatus


class ReportPublisher:
    """Turn one completed run into downloadable documents."""

    def __init__(self, templates: ReportTemplateRegistry, store: ConversationStore,
                 artifacts: ArtifactStore, workspace: Workspace,
                 reruns: ReportRerunService | None = None) -> None:
        self._templates = templates
        self._store = store
        self._artifacts = artifacts
        self._workspace = workspace
        self._reruns = reruns

    def templates(self) -> list[ReportTemplate]:
        return self._templates.list_templates()

    async def _resolve_content(
        self, *, run_id: str, metrics: list[MetricParameters] | None,
        period: str | None, narrative: NarrativeStatus | None,
    ) -> _ResolvedContent:
        """Gather what one run contributes to a report, once, for any consumer.

        With ``metrics``, the named sections are recomputed from their metric
        definitions and replace the run's own displays and evidence; without
        it, the run's persisted displays are used exactly as it created them.
        Either way this only assembles what already exists — it calls no model.
        """

        run = await self._store.get_run(run_id)
        if run is None:
            raise ReportPublishingError("Run not found.")
        if run.status != "completed":
            raise ReportPublishingError("Only a completed run can be published.")
        message = await self._store.get_assistant_message_for_run(run_id)

        charts = [ChartSpec.model_validate(item) for item in (getattr(run, "chart_specs", None) or [])]
        sources = [AnswerSource.model_validate(item) for item in (getattr(run, "answer_sources", None) or [])]

        analysis_period, status = period, narrative or "current"
        if metrics:
            if self._reruns is None:
                raise ReportPublishingError("Recomputing a report is not configured on this server.")
            try:
                outcomes = await self._reruns.run_all(run_id=run_id, requests=metrics)
            except ReportRerunError as error:
                raise ReportPublishingError(str(error)) from error
            # Recomputed figures replace the run's displays and cite their own
            # freshly minted evidence; the original prose never describes them.
            charts = [outcome.chart for outcome in outcomes]
            sources = [outcome.source for outcome in outcomes]
            period = _period_label(metrics)
            status = narrative or "excluded_from_refreshed_report"
        # Written by the model when it finished and stored with the run. Nothing
        # here asks for them again, so republishing prints the same limitations.
        caveats = normalize_caveats(list(getattr(run, "answer_caveats", None) or []))
        return _ResolvedContent(
            charts=charts, sources=sources, caveats=caveats, answer=message.content if message else "",
            period=period, analysis_period=analysis_period, narrative_status=status,
        )

    async def _compile(
        self, *, run_id: str, template_name: str, title: str | None,
        metrics: list[MetricParameters] | None, period: str | None, narrative: NarrativeStatus | None,
    ) -> tuple[ReportTemplate, _ResolvedContent, TemplateAssignment, CompiledReport]:
        """Resolve, assign and compile — the one path a preview and a publish share.

        Given the same run, template and parameters, this produces the same
        assignment and the same compiled report every time: assignment is a
        pure function of the resolved content, and nothing here is random,
        time-varying, or asks a model for an opinion.
        """

        try:
            template = self._templates.get(template_name)
        except ReportTemplateError as error:
            # A caller naming a template is a bad request, not a server fault.
            raise ReportPublishingError(str(error)) from error
        content = await self._resolve_content(run_id=run_id, metrics=metrics, period=period, narrative=narrative)
        assignment = assign_slots(template, content.charts, content.sources)
        content_order = assignment.content_order() if template.slots else None
        report = compile_report(
            template=template, run_id=run_id, answer=content.answer,
            charts=content.charts, sources=content.sources, generated_at=datetime.now(timezone.utc),
            period=content.period, title=title, caveats=content.caveats,
            narrative_status=content.narrative_status, analysis_period=content.analysis_period,
            content_order=content_order,
        )
        return template, content, assignment, report

    async def preview(
        self, *, run_id: str, template_name: str, period: str | None = None, title: str | None = None,
        metrics: list[MetricParameters] | None = None, narrative: NarrativeStatus | None = None,
    ) -> ReportPreview:
        """Compile the exact report a publish would produce, without writing one."""

        template, _content, assignment, report = await self._compile(
            run_id=run_id, template_name=template_name, title=title,
            metrics=metrics, period=period, narrative=narrative,
        )
        suitability = score_assignment(assignment)
        return ReportPreview(
            template_name=template.name, template_title=template.title, report=report,
            suitability=suitability, assignment=assignment,
            missing_required_content=missing_required_content(template, assignment),
            estimated_page_count=estimate_page_count(report),
        )

    async def suitability(self, *, run_id: str) -> TemplateSuitabilityOverview:
        """Score every template against one run's content, and recommend one."""

        # Parameter-free: this is "which shape fits what already exists",
        # asked before a caller has chosen a template, a period or a rerun.
        content = await self._resolve_content(run_id=run_id, metrics=None, period=None, narrative=None)
        items = [
            score_assignment(assign_slots(template, content.charts, content.sources))
            for template in self._templates.list_templates()
        ]
        return TemplateSuitabilityOverview(items=items, recommended_template=recommend_template(items))

    async def publish(self, *, run_id: str, template_name: str, formats: list[DocumentFormat],
                      period: str | None = None, title: str | None = None,
                      metrics: list[MetricParameters] | None = None,
                      narrative: NarrativeStatus | None = None) -> list[Artifact]:
        """Write the requested formats and register each as a downloadable artifact.

        Compiles through the same path ``preview`` uses, so a published
        document always matches the assignment a reader last saw.
        """

        template, content, _assignment, report = await self._compile(
            run_id=run_id, template_name=template_name, title=title,
            metrics=metrics, period=period, narrative=narrative,
        )
        return await render_and_register_documents(
            report=report, charts=content.charts, template=template, run_id=run_id, formats=formats,
            workspace=self._workspace, artifacts=self._artifacts,
            extra_metadata={"recomputed_metrics": [item.metric for item in (metrics or [])]},
        )
