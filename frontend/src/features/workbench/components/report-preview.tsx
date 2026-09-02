"use client";

import { useEffect, useState } from "react";
import { analyticsApi } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";
import { reportRequestPayload } from "@/features/workbench/report-request";
import type { MetricParameters, NarrativeStatus, ReportBlock, ReportPreview } from "@/types/analytics";

/** How long to wait after the last edit before asking the server to re-preview. */
const DEBOUNCE_MS = 350;

function blockOfKind<K extends ReportBlock["kind"]>(
  blocks: ReportBlock[],
  kind: K,
): Extract<ReportBlock, { kind: K }> | undefined {
  return blocks.find((block): block is Extract<ReportBlock, { kind: K }> => block.kind === kind);
}

/** Chart and table block titles, keyed by the id `create_chart` gave them. */
function displayTitles(blocks: ReportBlock[]): Map<string, string> {
  const titles = new Map<string, string>();
  for (const block of blocks) {
    if (block.kind === "chart") titles.set(block.chart_id, block.title);
    else if (block.kind === "table") titles.set(block.table_id, block.title);
  }
  return titles;
}

const NARRATIVE_MESSAGES: Record<string, string> = {
  pinned_to_original_period:
    "The written analysis describes a different period than the figures shown here.",
  excluded_from_refreshed_report:
    "The written analysis is left out because the figures were recomputed for a different period.",
};

/**
 * A deterministic, read-only preview of what publishing the current selection
 * will actually produce — the same compiled report a publish would compile,
 * shown before a PDF or DOCX is written. Nothing here calls a model.
 */
export function ReportPreviewPanel({
  runId,
  template,
  period,
  metrics,
  narrative,
}: {
  runId: string;
  template: string;
  period: string;
  metrics: MetricParameters[];
  narrative: NarrativeStatus;
}) {
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!template) return;
    let active = true;
    const timer = window.setTimeout(() => {
      void analyticsApi
        .previewReport(runId, reportRequestPayload({ template, period, metrics, narrative }))
        .then((result) => {
          if (!active) return;
          setPreview(result);
          setError(null);
        })
        .catch((cause: unknown) => {
          if (!active) return;
          setPreview(null);
          setError(cause instanceof ApiError ? cause.message : "The report preview is unavailable.");
        });
    }, DEBOUNCE_MS);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [runId, template, period, metrics, narrative]);

  if (!template) return null;
  if (error)
    return (
      <p className="report-preview-error" role="alert">
        {error}
      </p>
    );
  if (!preview) return null;

  const { report, suitability, assignment } = preview;
  const sections = report.blocks.map((block) => block.heading).filter((heading): heading is string => Boolean(heading));
  const titles = displayTitles(report.blocks);
  const metricsBlock = blockOfKind(report.blocks, "metrics");
  const caveatsBlock = blockOfKind(report.blocks, "caveats");
  const narrativeMessage =
    report.narrative_warning ?? NARRATIVE_MESSAGES[report.narrative_period_status];

  return (
    <section className="report-preview" aria-label="Report preview">
      <header>
        <strong>{preview.template_title}</strong>
        <span className={`report-preview-score ${suitability.can_publish ? "ok" : "warn"}`}>
          {suitability.completion_percentage}% complete
        </span>
      </header>
      <p className="report-preview-meta">
        {report.title}
        {report.displayed_period ? ` · ${report.displayed_period}` : ""} · ~{preview.estimated_page_count}{" "}
        page{preview.estimated_page_count === 1 ? "" : "s"}
      </p>

      {!suitability.can_publish && (
        <div className="report-preview-missing" role="alert">
          <strong>Missing required content</strong>
          <ul>
            {preview.missing_required_content.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}

      {sections.length > 0 && (
        <div className="report-preview-block">
          <strong>Sections</strong>
          <ol>
            {sections.map((heading) => (
              <li key={heading}>{heading}</li>
            ))}
          </ol>
        </div>
      )}

      {assignment.slots.length > 0 && (
        <div className="report-preview-block">
          <strong>Assigned content</strong>
          <ul className="report-preview-slots">
            {assignment.slots.map((slot) => (
              <li key={slot.slot_id}>
                <span className="report-preview-slot-name">{slot.slot_id.replaceAll("_", " ")}</span>
                <span className={slot.satisfied ? "ok" : slot.required ? "warn" : "muted"}>
                  {slot.assigned_chart_ids.length === 0
                    ? "none"
                    : slot.block_kind === "metrics"
                      ? `${metricsBlock?.metrics.length ?? slot.assigned_chart_ids.length} metric(s), below`
                      : slot.assigned_chart_ids.map((id) => titles.get(id) ?? id).join(", ")}
                </span>
              </li>
            ))}
          </ul>
          {metricsBlock && metricsBlock.metrics.length > 0 && (
            <p className="report-preview-metrics">
              Headline metrics: {metricsBlock.metrics.map((metric) => metric.label).join(", ")}
            </p>
          )}
          {assignment.unused_chart_ids.length > 0 && (
            <p className="report-preview-note">
              {assignment.unused_chart_ids.length} display(s) created during the run are not used by this
              template.
            </p>
          )}
        </div>
      )}

      <div className="report-preview-block">
        <strong>Evidence</strong>
        <p>{report.sources.length} citation(s) resolved.</p>
        {assignment.unresolved_evidence_chart_ids.length > 0 && (
          <p className="report-preview-note">
            {assignment.unresolved_evidence_chart_ids.length} display(s) excluded: their evidence is outside
            what this run resolved as evidence.
          </p>
        )}
      </div>

      {caveatsBlock && caveatsBlock.stated.length > 0 && (
        <div className="report-preview-block">
          <strong>Caveats</strong>
          <ul>
            {caveatsBlock.stated.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {narrativeMessage && (
        <p className="report-preview-note" role="status">
          {narrativeMessage}
        </p>
      )}

      <p className="report-preview-authority">{preview.pdf_authoritative_notice}</p>
    </section>
  );
}
