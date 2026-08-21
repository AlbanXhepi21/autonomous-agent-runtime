import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChartRenderer, prepareChart, xAxisLabelPolicy } from "./chart-renderer";

const chart = {
  id: "monthly-revenue",
  type: "line" as const,
  title: "Monthly Revenue for 2026",
  description: "Monthly revenue trend for 2026.",
  x_field: "month",
  y_fields: ["revenue"],
  series: [{ field: "revenue", label: "Revenue" }],
  data: [{ month: "2026-01", revenue: 14_000_000 }, { month: "2026-02", revenue: 18_000_000 }],
  source_query_ids: ["query_001"],
  created_at: "2026-01-01T00:00:00Z",
  kpis: [],
  formatting: { currency: "$", show_legend: true },
};

describe("ChartRenderer", () => {
  it("uses an adaptive, bounded category-label rule", () => {
    expect(xAxisLabelPolicy([{ product: "Camera" }], "product", "bar")).toMatchObject({ limit: 12, rotate: false, horizontalBars: false });
    expect(xAxisLabelPolicy([{ product: "Long Product Title" }], "product", "bar")).toMatchObject({ limit: 16, rotate: true, horizontalBars: false });
    expect(xAxisLabelPolicy([{ product: "An exceptionally long product category name" }], "product", "bar")).toMatchObject({ limit: 18, horizontalBars: true });
    expect(xAxisLabelPolicy([{ month: "2026-01" }], "month", "line")).toMatchObject({ isTime: true, includeYear: false, rotate: false, interval: 0 });
    expect(xAxisLabelPolicy([{ month: "2024-01-01" }, { month: "2025-01-01" }], "month", "line")).toMatchObject({ includeYear: true });
    expect(xAxisLabelPolicy(Array.from({ length: 24 }, (_, index) => ({ month: `2026-${String((index % 12) + 1).padStart(2, "0")}` })), "month", "line").interval).toBe(2);
  });

  it("pivots a repeated comparison category into chart series", () => {
    const prepared = prepareChart({ ...chart, type: "line", y_fields: ["orders"], series: [], data: [
      { month: "2026-01", customer_type: "New", orders: 10 }, { month: "2026-01", customer_type: "Returning", orders: 20 },
      { month: "2026-02", customer_type: "New", orders: 11 }, { month: "2026-02", customer_type: "Returning", orders: 21 },
    ] });
    expect(prepared.data).toHaveLength(2);
    expect(prepared.series.map((item) => item.label)).toEqual(["New", "Returning"]);
  });

  it("renders interactive display controls and its bounded source data", () => {
    render(<ChartRenderer chart={chart} />);
    expect(screen.getByText("Interactive")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Line" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Area" }));
    expect(screen.getByRole("button", { name: "Area" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Show data" }));
    expect(screen.getByText("2026-01")).toBeInTheDocument();
    expect(screen.getByText("$14M")).toBeInTheDocument();
  });
});
