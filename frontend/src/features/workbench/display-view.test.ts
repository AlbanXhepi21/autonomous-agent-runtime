import { describe, expect, it } from "vitest";
import {
  applyView,
  EMPTY_VIEW,
  filterableColumns,
  isViewActive,
  toggleFilterValue,
} from "./display-view";
import type { ChartSpec } from "@/types/displays";

const chart = {
  id: "chart-1",
  type: "bar",
  title: "Revenue by category",
  description: null,
  x_field: "category",
  y_fields: ["revenue"],
  series: [],
  data: [
    { category: "Electronics", country: "DE", revenue: 163 },
    { category: "Fashion", country: "DE", revenue: 63 },
    { category: "Garden", country: "FR", revenue: 20 },
  ],
  source_query_ids: ["query_003"],
  created_at: "",
  kpis: [],
  formatting: { currency: null, decimal_places: null, show_legend: true },
} as unknown as ChartSpec;

describe("display view", () => {
  it("offers dimensions to filter on and leaves measures out", () => {
    expect(filterableColumns(chart).map((column) => column.field)).toEqual(["category", "country"]);
  });

  it("keeps only the selected values", () => {
    const view = toggleFilterValue(EMPTY_VIEW, "country", "DE");

    expect(applyView(chart, view).data.map((row) => row.category)).toEqual([
      "Electronics",
      "Fashion",
    ]);
  });

  it("never changes a value it shows", () => {
    const view = toggleFilterValue(EMPTY_VIEW, "country", "DE");
    const filtered = applyView(chart, view);

    // Filtering selects rows; it must not recompute anything, or the display's
    // citation would no longer describe what is on screen.
    expect(filtered.data).toEqual(chart.data.filter((row) => row.country === "DE"));
    expect(filtered.source_query_ids).toEqual(chart.source_query_ids);
  });

  it("sorts numerically rather than lexically", () => {
    const view = { ...EMPTY_VIEW, sort: { field: "revenue", direction: "desc" as const } };

    expect(applyView(chart, view).data.map((row) => row.revenue)).toEqual([163, 63, 20]);
  });

  it("drops a filter once its last value is deselected", () => {
    const selected = toggleFilterValue(EMPTY_VIEW, "country", "DE");
    const cleared = toggleFilterValue(selected, "country", "DE");

    expect(cleared.filters).toEqual({});
    expect(isViewActive(cleared)).toBe(false);
  });

  it("returns the original display when the view changes nothing", () => {
    expect(applyView(chart, EMPTY_VIEW)).toBe(chart);
  });

  it("can filter a display down to nothing without failing", () => {
    const view = { ...EMPTY_VIEW, filters: { country: ["ES"] } };

    expect(applyView(chart, view).data).toEqual([]);
  });
});
