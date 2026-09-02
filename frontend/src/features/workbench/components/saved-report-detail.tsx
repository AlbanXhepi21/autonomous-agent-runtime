"use client";

import { useEffect, useState } from "react";
import { artifactsApi } from "@/lib/api/artifacts";
import type { useSavedReports } from "@/features/workbench/hooks/use-saved-reports";
import type { DocumentFormat } from "@/types/analytics";
import type { NarrativePolicy, RelativePeriodKind, SavedReport } from "@/types/saved-reports";

const PERIOD_KINDS: { value: RelativePeriodKind; label: string }[] = [
  { value: "current_month", label: "Current calendar month" },
  { value: "previous_month", label: "Previous calendar month" },
  { value: "current_quarter", label: "Current calendar quarter" },
  { value: "previous_quarter", label: "Previous calendar quarter" },
  { value: "current_year", label: "Current calendar year" },
  { value: "previous_year", label: "Previous calendar year" },
  { value: "last_n_days", label: "Last N complete days" },
  { value: "fixed", label: "Fixed date range" },
];

const FORMATS: { value: DocumentFormat; label: string }[] = [
  { value: "pdf", label: "PDF" },
  { value: "docx", label: "Word" },
];

type SavedReportsState = ReturnType<typeof useSavedReports>;

/**
 * Reopen a saved report: review its recipe, edit its parameters and
 * presentation, run it again, and see what earlier runs produced.
 *
 * A thin shell over `SavedReportDetailBody`, which owns the actual form
 * state. The body is keyed by the report's id so switching to a different
 * saved report remounts it with fresh state, rather than syncing local state
 * from `detail` inside an effect.
 */
export function SavedReportDetail({ state, onClose }: { state: SavedReportsState; onClose: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!state.detail) return null;

  return (
    <div className="display-panel-backdrop" onClick={onClose}>
      <SavedReportDetailBody key={state.detail.id} detail={state.detail} state={state} onClose={onClose} />
    </div>
  );
}

function SavedReportDetailBody({
  detail,
  state,
  onClose,
}: {
  detail: SavedReport;
  state: SavedReportsState;
  onClose: () => void;
}) {
  const { resolvedParameters, executions, busy, error, lastResult } = state;
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(detail.name);
  const [description, setDescription] = useState(detail.description ?? "");
  const [narrativePolicy, setNarrativePolicy] = useState<NarrativePolicy>(detail.narrative_policy);
  const [periodKind, setPeriodKind] = useState<RelativePeriodKind>(detail.default_period.kind);
  const [days, setDays] = useState(detail.default_period.days ?? 30);
  const [fixedStart, setFixedStart] = useState(detail.default_period.start ?? "");
  const [fixedEnd, setFixedEnd] = useState(detail.default_period.end ?? "");
  const [mode, setMode] = useState<"preview" | "publish">("preview");
  const [formats, setFormats] = useState<DocumentFormat[]>(["pdf"]);
  const [confirmArchive, setConfirmArchive] = useState(false);

  const canIncludeOriginal = Boolean(detail.seed_narrative);

  const saveEdits = async () => {
    const updated = await state.update({
      name: name.trim() || detail.name,
      description: description.trim() || null,
      narrative_policy: narrativePolicy,
      default_period:
        periodKind === "last_n_days"
          ? { kind: "last_n_days", days }
          : periodKind === "fixed"
            ? { kind: "fixed", start: fixedStart, end: fixedEnd }
            : { kind: periodKind },
    });
    if (updated) setEditing(false);
  };

  const run = async () => {
    await state.execute(mode, formats);
  };

  return (
    <aside
      className="display-panel saved-report-detail"
      onClick={(event) => event.stopPropagation()}
      aria-label={`Saved report: ${detail.name}`}
    >
      <header>
        <strong>{detail.name}</strong>
        <button type="button" onClick={onClose} aria-label="Close saved report">
          ✕
        </button>
      </header>

      {error && (
        <p className="report-export-error" role="alert">
          {error}
        </p>
      )}

      <p className="report-export-note">
        {detail.template_id} · pinned version {detail.template_version}
        {resolvedParameters && !resolvedParameters.template_version_matches_pin && (
          <> · current version {resolvedParameters.current_template_version} — will be noted as a caveat</>
        )}
        {" · "}
        {detail.status} · v{detail.version}
      </p>

      {resolvedParameters && (
        <p className="report-export-note">
          Runs now would cover {resolvedParameters.resolved_period_description} (
          {resolvedParameters.resolved_period_start} to {resolvedParameters.resolved_period_end})
        </p>
      )}

      <div className="report-preview-block">
        <strong>Metrics</strong>
        <ul>
          {detail.metric_requests.map((item, index) => (
            <li key={`${item.metric}-${index}`}>
              {item.metric}
              {item.dimensions.length ? ` · by ${item.dimensions.join(", ")}` : ""}
              {item.filters.length ? ` · ${item.filters.length} filter(s)` : ""}
            </li>
          ))}
        </ul>
      </div>

      {!editing ? (
        <button type="button" onClick={() => setEditing(true)}>
          Edit parameters
        </button>
      ) : (
        <section className="save-report-form" aria-label="Edit saved report parameters">
          <label>
            <span>Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            <span>Description</span>
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label>
            <span>Default period</span>
            <select value={periodKind} onChange={(event) => setPeriodKind(event.target.value as RelativePeriodKind)}>
              {PERIOD_KINDS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          {periodKind === "last_n_days" && (
            <label>
              <span>Days</span>
              <input type="number" min={1} value={days} onChange={(event) => setDays(Number(event.target.value))} />
            </label>
          )}
          {periodKind === "fixed" && (
            <div className="report-refresh-row">
              <label>
                <span>From</span>
                <input type="date" value={fixedStart} onChange={(event) => setFixedStart(event.target.value)} />
              </label>
              <label>
                <span>To</span>
                <input type="date" value={fixedEnd} onChange={(event) => setFixedEnd(event.target.value)} />
              </label>
            </div>
          )}
          <fieldset>
            <legend>Written analysis</legend>
            <label>
              <input
                type="radio"
                name="edit-narrative-policy"
                checked={narrativePolicy === "exclude"}
                onChange={() => setNarrativePolicy("exclude")}
              />
              <span>Never include prose</span>
            </label>
            <label>
              <input
                type="radio"
                name="edit-narrative-policy"
                checked={narrativePolicy === "include_original"}
                disabled={!canIncludeOriginal}
                onChange={() => setNarrativePolicy("include_original")}
              />
              <span>Reuse the saved prose, with a pinned-period warning</span>
            </label>
            <label>
              <input
                type="radio"
                name="edit-narrative-policy"
                checked={narrativePolicy === "require_new_investigation"}
                onChange={() => setNarrativePolicy("require_new_investigation")}
              />
              <span>Require a fresh investigation each time</span>
            </label>
          </fieldset>
          <div className="report-refresh-row">
            <button type="button" className="report-export-run" disabled={busy} onClick={() => void saveEdits()}>
              Save changes
            </button>
            <button type="button" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </section>
      )}

      {detail.narrative_policy === "require_new_investigation" ? (
        <p className="report-export-note">
          This saved report requires a new agent investigation. Ask a fresh question in the Workbench to
          produce one — running it here never calls a model.
        </p>
      ) : (
        <section className="save-report-form" aria-label="Run this saved report">
          <strong>Run now</strong>
          <div className="report-refresh-row">
            <label>
              <span>Mode</span>
              <select value={mode} onChange={(event) => setMode(event.target.value as "preview" | "publish")}>
                <option value="preview">Preview only</option>
                <option value="publish">Publish document</option>
              </select>
            </label>
            {mode === "publish" && (
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
                            ? current.filter((item) => item !== format.value)
                            : [...current, format.value],
                        )
                      }
                    >
                      {format.label}
                    </button>
                  );
                })}
              </fieldset>
            )}
            <button
              type="button"
              className="report-export-run"
              disabled={busy || (mode === "publish" && formats.length === 0)}
              onClick={() => void run()}
            >
              {busy ? "Running…" : "Run"}
            </button>
          </div>

          {lastResult?.preview && (
            <p className="report-export-note">
              {lastResult.preview.suitability.completion_percentage}% complete ·{" "}
              {lastResult.preview.suitability.can_publish ? "ready to publish" : "missing required content"}
            </p>
          )}
          {lastResult && lastResult.documents.length > 0 && (
            <ul className="report-export-results">
              {lastResult.documents.map((document) => (
                <li key={document.artifact_id}>
                  <a href={artifactsApi.downloadUrl(document.artifact_id)}>
                    Download {document.name} ({Math.round(document.size / 1024)} KB)
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="report-preview-block">
        <strong>Execution history</strong>
        {executions.length === 0 && <p className="report-export-note">No executions yet.</p>}
        <ul>
          {executions.map((execution) => (
            <li key={execution.id}>
              {execution.mode} · {execution.status}
              {execution.resolved_period_start && execution.resolved_period_end
                ? ` · ${execution.resolved_period_start} to ${execution.resolved_period_end}`
                : ""}
              {execution.error ? ` · ${execution.error}` : ""}
              {execution.artifacts.map((artifact) => (
                <span key={artifact.artifact_id}>
                  {" "}
                  · <a href={artifactsApi.downloadUrl(artifact.artifact_id)}>{artifact.name}</a>
                </span>
              ))}
            </li>
          ))}
        </ul>
      </div>

      {detail.status === "active" && (
        <button
          type="button"
          className="delete-conversation"
          onClick={() => {
            if (!confirmArchive) {
              setConfirmArchive(true);
              return;
            }
            void state.archive();
          }}
        >
          {confirmArchive ? "Confirm archive" : "Archive this report"}
        </button>
      )}
    </aside>
  );
}
