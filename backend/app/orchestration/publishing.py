"""Publish a stored run as a document.

Everything a report needs — the written answer, the displays, the evidence
registry — is already persisted with the run, so publishing is a deterministic
assembly rather than another agent turn. That keeps a re-export of the same run
byte-comparable in content, costs no tokens, and removes any chance of the
model quietly rewriting an analysis someone already signed off.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from app.analytics.presentation.charts import ChartSpec
from app.analytics.presentation.documents import write_docx, write_pdf
from app.analytics.presentation.compiler import compile_report
from app.analytics.presentation.rasterize import render_chart_png
from app.analytics.presentation.templates import (
    ReportTemplate,
    ReportTemplateError,
    ReportTemplateRegistry,
)
from app.artifacts.contracts import Artifact
from app.artifacts.store import ArtifactStore
from app.analytics.presentation.document_model import NarrativeStatus
from app.analytics.semantics.parameters import MetricParameters
from app.contracts.actions import normalize_caveats
from app.contracts.answers import AnswerSource
from app.orchestration.reruns import ReportRerunError, ReportRerunService
from app.conversations.store import ConversationStore
from app.core.logging import log_event
from app.environment.workspace import Workspace

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

    async def publish(self, *, run_id: str, template_name: str, formats: list[DocumentFormat],
                      period: str | None = None, title: str | None = None,
                      metrics: list[MetricParameters] | None = None,
                      narrative: NarrativeStatus | None = None) -> list[Artifact]:
        """Write the requested formats and register each as a downloadable artifact.

        With ``metrics``, the named sections are recomputed from their metric
        definitions before the document is assembled, and the run's own prose is
        either kept under a warning or left out — never quietly reused. Both
        paths are deterministic assembly; neither calls a model.
        """

        try:
            template = self._templates.get(template_name)
        except ReportTemplateError as error:
            # A caller naming a template is a bad request, not a server fault.
            raise ReportPublishingError(str(error)) from error
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
        report = compile_report(
            template=template, run_id=run_id, answer=message.content if message else "",
            charts=charts, sources=sources, generated_at=datetime.now(timezone.utc),
            period=period, title=title, caveats=caveats,
            narrative_status=status, analysis_period=analysis_period,
        )

        directory = self._workspace.root / ".runtime" / "published" / run_id
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
                artifact = await self._artifacts.register(
                    run_id=run_id, source_path=path.relative_to(self._workspace.root).as_posix(),
                    artifact_type="report_document", media_type=media_type,
                    output_format=document_format, template_id=template.name,
                    template_version=template.version,
                    metadata={"template": template.name, "report_type": template.report_type.value,
                              "period": period or "", "chart_count": len(images),
                              "caveat_count": sum(len(block.stated) for block in report.blocks_of("caveats")),
                              "narrative_status": report.narrative_period_status,
                              "recomputed_metrics": [item.metric for item in (metrics or [])],
                              "report_id": report.report_id,
                              "orientation": report.orientation,
                              "source_query_ids": report.cited_query_ids},
                )
            except (OSError, ValueError) as error:
                raise ReportPublishingError("The report could not be written within configured limits.") from error
            published.append(artifact)
            log_event(_logger, logging.INFO, "report_published", run_id=run_id,
                      template=template.name, document_format=document_format,
                      chart_count=len(images), size=artifact.size)
        return published
