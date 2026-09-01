"use client";

import { useEffect, useState } from "react";
import { analyticsApi } from "@/lib/api/analytics";
import { artifactsApi } from "@/lib/api/artifacts";
import { ApiError } from "@/lib/api/client";
import { ReportRefresh } from "@/features/workbench/components/report-refresh";
import type {
  DocumentFormat,
  MetricParameters,
  NarrativeStatus,
  PublishedDocument,
  ReportTemplate,
} from "@/types/analytics";

const FORMATS: { value: DocumentFormat; label: string }[] = [
  { value: "pdf", label: "PDF" },
  { value: "docx", label: "Word" },
];

/**
 * Publish a finished analysis as a document.
 *
 * The run already holds its answer, displays and evidence, so this asks the
 * server to assemble them — no second pass by the model, and therefore the same
 * figures and the same citations the reader saw in the Workbench.
 */
export function ReportExport({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [template, setTemplate] = useState("");
  const [formats, setFormats] = useState<DocumentFormat[]>(["pdf"]);
  const [period, setPeriod] = useState("");
  const [busy, setBusy] = useState(false);
  const [documents, setDocuments] = useState<PublishedDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MetricParameters[]>([]);
  const [narrative, setNarrative] = useState<NarrativeStatus>("excluded_from_refreshed_report");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!open || templates.length) return;
    void analyticsApi
      .reportTemplates()
      .then((body) => {
        setTemplates(body.items);
        setTemplate((current) => current || (body.items[0]?.name ?? ""));
      })
      .catch(() => setError("Report templates are unavailable."));
  }, [open, templates.length]);

  const selected = templates.find((item) => item.name === template);

  const publish = async () => {
    setBusy(true);
    setError(null);
    setDocuments([]);
    setNotice(null);
    try {
      const result = await analyticsApi.publishReport(runId, {
        template,
        formats,
        ...(period.trim() ? { period: period.trim() } : {}),
        ...(metrics.length ? { metrics, narrative } : {}),
      });
      setDocuments(result.documents);
      if (result.narrative === "excluded_from_refreshed_report" && metrics.length) {
        setNotice(
          "Figures were recomputed. The written analysis was left out because it " +
            "describes the original period.",
        );
      } else if (result.narrative === "pinned_to_original_period") {
        setNotice(
          "Figures were recomputed. The written analysis is included with a warning " +
            "that it describes the original period.",
        );
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The report could not be generated.");
    } finally {
      setBusy(false);
    }
  };

  if (!open)
    return (
      <button type="button" className="report-export-open" onClick={() => setOpen(true)}>
        Export report
      </button>
    );

  return (
    <section className="report-export" aria-label="Export this analysis as a report">
      <header>
        <strong>Export report</strong>
        <button type="button" onClick={() => setOpen(false)} aria-label="Close export options">
          ✕
        </button>
      </header>

      <label>
        <span>Template</span>
        <select value={template} onChange={(event) => setTemplate(event.target.value)}>
          {templates.map((item) => (
            <option key={item.name} value={item.name}>
              {item.title}
            </option>
          ))}
        </select>
      </label>
      {selected && <p className="report-export-note">{selected.description}</p>}

      <label>
        <span>Period covered</span>
        <input
          value={period}
          placeholder={selected?.period_granularity === "year" ? "2026" : "August 2026"}
          onChange={(event) => setPeriod(event.target.value)}
        />
      </label>
      <p className="report-export-note">
        Optional, and printed exactly as typed. The runtime cannot tell which period an analysis
        covered, so it never guesses one.
      </p>

      <fieldset>
        <legend>Format</legend>
        {FORMATS.map((format) => {
          const active = formats.includes(format.value);
          return (
            <button
              key={format.value}
              type="button"
              aria-pressed={active}
              className={active ? "active" : ""}
              onClick={() =>
                setFormats((current) =>
                  current.includes(format.value)
                    ? current.filter((item) => item !== format.value) || []
                    : [...current, format.value],
                )
              }
            >
              {format.label}
            </button>
          );
        })}
      </fieldset>

      <ReportRefresh
        value={metrics}
        narrative={narrative}
        onChange={setMetrics}
        onNarrativeChange={setNarrative}
      />

      <button
        type="button"
        className="report-export-run"
        disabled={busy || !template || formats.length === 0}
        onClick={() => void publish()}
      >
        {busy ? "Generating…" : metrics.length ? "Generate with refreshed figures" : "Generate"}
      </button>

      {error && (
        <p className="report-export-error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="report-export-notice" role="status">
          {notice}
        </p>
      )}
      {documents.length > 0 && (
        <ul className="report-export-results">
          {documents.map((document) => (
            <li key={document.artifact_id}>
              <a href={artifactsApi.downloadUrl(document.artifact_id)}>
                Download {document.name} ({Math.round(document.size / 1024)} KB)
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
