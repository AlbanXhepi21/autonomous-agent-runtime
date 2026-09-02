"use client";

import { useState } from "react";
import { savedReportsApi } from "@/lib/api/saved-reports";
import { ApiError } from "@/lib/api/client";
import type { MetricParameters } from "@/types/analytics";
import type { NarrativePolicy, RelativePeriodKind } from "@/types/saved-reports";

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

/**
 * Save the current report configuration as a durable, rerunnable recipe.
 *
 * A saved report only ever describes metric requests — the same ones
 * `ReportRefresh` recomputes for a one-off export — so this is only
 * available once at least one has been chosen. What is saved is the recipe,
 * never a value: the numbers a future run shows come from executing it
 * again, not from anything typed here.
 */
export function SaveReportForm({
  runId,
  template,
  metrics,
  narrativeText,
  onSaved,
}: {
  runId: string;
  template: string;
  metrics: MetricParameters[];
  narrativeText: string;
  onSaved?: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [periodKind, setPeriodKind] = useState<RelativePeriodKind>("last_n_days");
  const [days, setDays] = useState(30);
  const [fixedStart, setFixedStart] = useState("");
  const [fixedEnd, setFixedEnd] = useState("");
  const [narrativePolicy, setNarrativePolicy] = useState<NarrativePolicy>("exclude");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  if (!metrics.length) {
    return (
      <p className="report-export-note">
        Choose one or more metrics to recompute above before saving this as a rerunnable report.
      </p>
    );
  }

  const canIncludeOriginal = Boolean(narrativeText.trim());
  const periodValid =
    periodKind !== "last_n_days" && periodKind !== "fixed"
      ? true
      : periodKind === "last_n_days"
        ? days >= 1
        : Boolean(fixedStart && fixedEnd && fixedEnd > fixedStart);
  const canSave = Boolean(name.trim()) && periodValid && !busy;

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const report = await savedReportsApi.create({
        workspace_id: "default",
        name: name.trim(),
        template_id: template,
        metric_requests: metrics.map((item) => ({
          metric: item.metric,
          dimensions: item.dimensions ?? [],
          filters: item.filters ?? [],
          grain: item.grain,
        })),
        default_period:
          periodKind === "last_n_days"
            ? { kind: "last_n_days", days }
            : periodKind === "fixed"
              ? { kind: "fixed", start: fixedStart, end: fixedEnd }
              : { kind: periodKind },
        narrative_policy: narrativePolicy,
        ...(narrativePolicy === "include_original"
          ? { seed_run_id: runId, seed_narrative: narrativeText }
          : {}),
      });
      setSavedId(report.id);
      onSaved?.(report.id);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "This report could not be saved.");
    } finally {
      setBusy(false);
    }
  };

  if (!open)
    return (
      <button type="button" className="report-export-open" onClick={() => setOpen(true)}>
        Save as report…
      </button>
    );

  return (
    <section className="save-report-form" aria-label="Save this report configuration">
      <header>
        <strong>Save as report</strong>
        <button type="button" onClick={() => setOpen(false)} aria-label="Close save form">
          ✕
        </button>
      </header>

      {savedId ? (
        <p className="report-export-notice" role="status">
          Saved. Reopen it from Saved Reports in the sidebar to run it again.
        </p>
      ) : (
        <>
          <label>
            <span>Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Weekly revenue" />
          </label>

          <label>
            <span>Default period</span>
            <select
              value={periodKind}
              onChange={(event) => setPeriodKind(event.target.value as RelativePeriodKind)}
            >
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
              <input
                type="number"
                min={1}
                value={days}
                onChange={(event) => setDays(Number(event.target.value))}
              />
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
          <p className="report-export-note">
            Resolved fresh, in UTC, every time this report runs — never a fixed date remembered from today.
          </p>

          <fieldset>
            <legend>Written analysis</legend>
            <label>
              <input
                type="radio"
                name="saved-narrative-policy"
                checked={narrativePolicy === "exclude"}
                onChange={() => setNarrativePolicy("exclude")}
              />
              <span>Never include prose — figures only, every time</span>
            </label>
            <label>
              <input
                type="radio"
                name="saved-narrative-policy"
                checked={narrativePolicy === "include_original"}
                disabled={!canIncludeOriginal}
                onChange={() => setNarrativePolicy("include_original")}
              />
              <span>
                Reuse this analysis&apos;s prose, with a pinned-period warning
                {!canIncludeOriginal && " (keep the original prose above to enable this)"}
              </span>
            </label>
            <label>
              <input
                type="radio"
                name="saved-narrative-policy"
                checked={narrativePolicy === "require_new_investigation"}
                onChange={() => setNarrativePolicy("require_new_investigation")}
              />
              <span>Require a fresh investigation each time — never run automatically</span>
            </label>
          </fieldset>

          <button type="button" className="report-export-run" disabled={!canSave} onClick={() => void save()}>
            {busy ? "Saving…" : "Save report"}
          </button>
          {error && (
            <p className="report-export-error" role="alert">
              {error}
            </p>
          )}
        </>
      )}
    </section>
  );
}
