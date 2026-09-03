"use client";

import { useEffect, useState } from "react";
import { analyticsApi } from "@/lib/api/analytics";
import { useWorkspaceId } from "@/features/workbench/workspace-context";
import type { MetricParameters, NarrativeStatus, RerunMetric } from "@/types/analytics";

/**
 * Recompute a report's figures for a different period.
 *
 * Everything offered here comes from the metric definitions the server
 * publishes: the metrics, the groupings and the filterable fields. The reader
 * chooses among them and supplies dates — never a column, an expression or a
 * value that becomes part of a query. The server compiles the statement, so
 * there is nothing this form could send that would change what SQL runs.
 *
 * The prose is the reader's other decision. It was written for the original
 * period and cannot be rewritten without asking the model again, so the choice
 * is to drop it or to keep it under a warning. There is no option that quietly
 * reuses it.
 */
export function ReportRefresh({
  value,
  narrative,
  onChange,
  onNarrativeChange,
}: {
  value: MetricParameters[];
  narrative: NarrativeStatus;
  onChange: (metrics: MetricParameters[]) => void;
  onNarrativeChange: (status: NarrativeStatus) => void;
}) {
  const workspaceId = useWorkspaceId();
  const [metrics, setMetrics] = useState<RerunMetric[]>([]);
  const [metric, setMetric] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [dimension, setDimension] = useState("");
  const [grain, setGrain] = useState<MetricParameters["grain"]>("month");

  useEffect(() => {
    void analyticsApi
      .rerunMetrics(workspaceId)
      .then((body) => {
        setMetrics(body.items);
        setMetric((current) => current || (body.items[0]?.name ?? ""));
      })
      .catch(() => setMetrics([]));
  }, [workspaceId]);

  const selected = metrics.find((item) => item.name === metric);
  const enabled = Boolean(metric && start && end && end > start);

  const add = () => {
    if (!enabled) return;
    onChange([
      ...value,
      {
        metric,
        period: { start, end },
        // Sent explicitly rather than left to the server default, so what the
        // reader chose and what runs are visibly the same thing.
        grain,
        ...(dimension ? { dimensions: [dimension] } : {}),
      },
    ]);
    setDimension("");
  };

  if (!metrics.length) return null;

  return (
    <section className="report-refresh" aria-label="Recompute report figures">
      <p className="report-refresh-lead">Recompute figures</p>
      <p className="report-export-note">
        Recomputed from the metric definitions for the period you choose. The original analysis is
        not re-run and no model is called.
      </p>

      <div className="report-refresh-row">
        <label>
          <span>Metric</span>
          <select value={metric} onChange={(event) => setMetric(event.target.value)}>
            {metrics.map((item) => (
              <option key={item.name} value={item.name}>
                {item.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>From</span>
          <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label>
          <span>To</span>
          <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
        <label>
          <span>Group by</span>
          <select value={dimension} onChange={(event) => setDimension(event.target.value)}>
            <option value="">No grouping</option>
            {(selected?.dimensions ?? []).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        {dimension === "period" && (
          <label>
            <span>Bucket</span>
            <select
              value={grain}
              onChange={(event) => setGrain(event.target.value as MetricParameters["grain"])}
            >
              {(selected?.grains ?? []).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        )}
        <button type="button" onClick={add} disabled={!enabled}>
          Add
        </button>
      </div>

      {value.length > 0 && (
        <>
          <ul className="report-refresh-list">
            {value.map((item, index) => (
              <li key={`${item.metric}-${index}`}>
                <span>
                  {item.metric} · {item.period.start} to {item.period.end}
                  {item.dimensions?.length
                    ? ` · by ${item.dimensions.join(", ")}${
                        item.dimensions.includes("period") ? ` (${item.grain})` : ""
                      }`
                    : ""}
                </span>
                <button
                  type="button"
                  aria-label={`Remove ${item.metric}`}
                  onClick={() => onChange(value.filter((_, position) => position !== index))}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>

          <fieldset className="report-refresh-narrative">
            <legend>Written analysis</legend>
            <label>
              <input
                type="radio"
                name="narrative"
                checked={narrative === "excluded_from_refreshed_report"}
                onChange={() => onNarrativeChange("excluded_from_refreshed_report")}
              />
              <span>Leave it out — export the refreshed figures only</span>
            </label>
            <label>
              <input
                type="radio"
                name="narrative"
                checked={narrative === "pinned_to_original_period"}
                onChange={() => onNarrativeChange("pinned_to_original_period")}
              />
              <span>Keep it, with a visible warning that it describes the original period</span>
            </label>
            <p className="report-export-note">
              To get prose written for the new period, ask a new question in the Workbench. That is
              a fresh investigation, not an export.
            </p>
          </fieldset>
        </>
      )}
    </section>
  );
}
