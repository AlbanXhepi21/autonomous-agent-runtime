import type { ChartSpec } from "@/types/displays";

/**
 * Reading a display without changing what it says.
 *
 * A view only ever selects and reorders rows the query already returned, so a
 * filtered display still rests on the same evidence and keeps its citation.
 * Nothing here recomputes a value, derives a column, or invents a row — that
 * would make the display's provenance a lie.
 */
export type DisplayFilters = Record<string, string[]>;
export type DisplaySort = { field: string; direction: "asc" | "desc" } | null;

export interface DisplayView {
  /** Column to the values kept. An absent or empty entry keeps every value. */
  filters: DisplayFilters;
  sort: DisplaySort;
}

export interface FilterableColumn {
  field: string;
  values: string[];
}

export const EMPTY_VIEW: DisplayView = { filters: {}, sort: null };

/** The most distinct values a column may hold and still be worth filtering on. */
const MAX_FILTER_VALUES = 24;

export function isViewActive(view: DisplayView): boolean {
  return view.sort !== null || Object.values(view.filters).some((values) => values.length > 0);
}

/**
 * Columns a reader can filter by.
 *
 * Measures are excluded: filtering revenue to a set of exact amounts is not a
 * question anyone asks. A column with one distinct value cannot narrow
 * anything, and one with very many would render as an unusable list.
 */
export function filterableColumns(chart: ChartSpec): FilterableColumn[] {
  const measures = new Set([...chart.y_fields, ...chart.series.map((series) => series.field)]);
  const columns = Object.keys(chart.data[0] ?? {});
  const filterable: FilterableColumn[] = [];
  for (const field of columns) {
    if (measures.has(field)) continue;
    const values = new Set<string>();
    let categorical = true;
    for (const row of chart.data) {
      const value = row[field];
      if (typeof value === "number") {
        categorical = false;
        break;
      }
      if (value === null || value === undefined) continue;
      values.add(String(value));
    }
    if (!categorical || values.size < 2 || values.size > MAX_FILTER_VALUES) continue;
    filterable.push({ field, values: [...values].sort() });
  }
  return filterable;
}

/** Columns a reader can sort by, measures included. */
export function sortableColumns(chart: ChartSpec): string[] {
  return Object.keys(chart.data[0] ?? {});
}

function compare(left: unknown, right: unknown): number {
  if (typeof left === "number" && typeof right === "number") return left - right;
  return String(left ?? "").localeCompare(String(right ?? ""), undefined, { numeric: true });
}

/** Apply a view, returning a display whose rows are a subset of the original. */
export function applyView(chart: ChartSpec, view: DisplayView): ChartSpec {
  let data = chart.data;
  for (const [field, kept] of Object.entries(view.filters)) {
    if (!kept.length) continue;
    const wanted = new Set(kept);
    data = data.filter((row) => wanted.has(String(row[field])));
  }
  if (view.sort) {
    const { field, direction } = view.sort;
    const factor = direction === "asc" ? 1 : -1;
    data = [...data].sort((left, right) => factor * compare(left[field], right[field]));
  }
  return data === chart.data ? chart : { ...chart, data };
}

/** Toggle one value of one filter, dropping the entry when nothing is selected. */
export function toggleFilterValue(view: DisplayView, field: string, value: string): DisplayView {
  const current = view.filters[field] ?? [];
  const next = current.includes(value)
    ? current.filter((item) => item !== value)
    : [...current, value];
  const filters = { ...view.filters };
  if (next.length) filters[field] = next;
  else delete filters[field];
  return { ...view, filters };
}
