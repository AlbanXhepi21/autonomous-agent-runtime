"use client";

import { useEffect, useMemo, useState } from "react";
import { ChartRenderer } from "@/features/workbench/components/chart-renderer";
import {
  applyView,
  EMPTY_VIEW,
  filterableColumns,
  isViewActive,
  sortableColumns,
  toggleFilterValue,
  type DisplayView,
} from "@/features/workbench/display-view";
import type { AnswerSource } from "@/types/analytics";
import type { ChartSpec } from "@/types/displays";

interface Props {
  chart: ChartSpec;
  /** The run's evidence registry, used to state what the display was drawn from. */
  sources: AnswerSource[];
  onClose: () => void;
}

/**
 * Say what the reader is filtering over.
 *
 * A display carries at most the rows the agent copied into it, which can be far
 * fewer than the query returned. Without this, filtering to a value that never
 * made it into the display looks like an empty result rather than a display
 * that never held the value.
 */
function population(chart: ChartSpec, sources: AnswerSource[]): string | null {
  const cited = sources.filter((source) => chart.source_query_ids.includes(source.id));
  const queried = cited.reduce<number | null>(
    (total, source) => (source.row_count === null ? total : (total ?? 0) + source.row_count),
    null,
  );
  if (queried === null || queried <= chart.data.length) return null;
  return `This display holds ${chart.data.length} of the ${queried.toLocaleString()} rows the source query returned. Filters apply to those ${chart.data.length}.`;
}

export function DisplayPanel({ chart, sources, onClose }: Props) {
  const [view, setView] = useState<DisplayView>(EMPTY_VIEW);
  const filters = useMemo(() => filterableColumns(chart), [chart]);
  const sortable = useMemo(() => sortableColumns(chart), [chart]);
  const viewed = useMemo(() => applyView(chart, view), [chart, view]);
  const note = useMemo(() => population(chart, sources), [chart, sources]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="display-panel-backdrop" onClick={onClose}>
      <aside
        className="display-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Explore ${chart.title}`}
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span className="eyebrow">EXPLORE</span>
            <h2>{chart.title}</h2>
          </div>
          <button
            type="button"
            className="display-panel-close"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        <div className="display-panel-body">
          <p className="display-panel-count">
            Showing {viewed.data.length} of {chart.data.length} rows
            {isViewActive(view) && (
              <button
                type="button"
                className="display-panel-reset"
                onClick={() => setView(EMPTY_VIEW)}
              >
                Reset
              </button>
            )}
          </p>
          {note && <p className="display-panel-note">{note}</p>}

          {filters.map((column) => (
            <fieldset className="display-filter" key={column.field}>
              <legend>{column.field}</legend>
              {column.values.map((value) => {
                const active = (view.filters[column.field] ?? []).includes(value);
                return (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={active}
                    className={active ? "active" : ""}
                    onClick={() =>
                      setView((current) => toggleFilterValue(current, column.field, value))
                    }
                  >
                    {value}
                  </button>
                );
              })}
            </fieldset>
          ))}

          <fieldset className="display-filter">
            <legend>sort</legend>
            <select
              aria-label="Sort by"
              value={view.sort?.field ?? ""}
              onChange={(event) =>
                setView((current) => ({
                  ...current,
                  sort: event.target.value
                    ? { field: event.target.value, direction: current.sort?.direction ?? "desc" }
                    : null,
                }))
              }
            >
              <option value="">Original order</option>
              {sortable.map((field) => (
                <option key={field} value={field}>
                  {field}
                </option>
              ))}
            </select>
            {view.sort && (
              <button
                type="button"
                onClick={() =>
                  setView((current) => ({
                    ...current,
                    sort: current.sort
                      ? {
                          ...current.sort,
                          direction: current.sort.direction === "asc" ? "desc" : "asc",
                        }
                      : null,
                  }))
                }
              >
                {view.sort.direction === "asc" ? "Ascending" : "Descending"}
              </button>
            )}
          </fieldset>

          {viewed.data.length === 0 ? (
            <p className="display-empty">No rows match these filters.</p>
          ) : (
            <ChartRenderer chart={viewed} />
          )}
        </div>
      </aside>
    </div>
  );
}
