import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DisplayPanel } from "./display-panel";
import type { AnswerSource } from "@/types/analytics";
import type { ChartSpec } from "@/types/displays";

const chart = {
  id: "chart-1",
  type: "table",
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

const source: AnswerSource = {
  id: "query_003",
  kind: "database_query",
  run_id: "run-1",
  label: "Revenue by category",
  referenced_tables: ["orders"],
  columns: [],
  metric: null,
  dimensions: [],
  filters: [],
  sql_fingerprint: null,
  row_count: 4200,
  truncated: false,
  executed_at: "2026-08-22T13:31:00Z",
};

describe("DisplayPanel", () => {
  it("narrows the rows shown and reports how many remain", () => {
    render(<DisplayPanel chart={chart} sources={[]} onClose={vi.fn()} />);
    expect(screen.getByText("Showing 3 of 3 rows")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "FR" }));

    // Scoped to the table: the filter buttons keep offering every value, so a
    // deselected one must stay clickable even once its rows are hidden.
    const table = within(screen.getByRole("table"));
    expect(screen.getByText("Showing 1 of 3 rows")).toBeInTheDocument();
    expect(table.getByText("Garden")).toBeInTheDocument();
    expect(table.queryByText("Electronics")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Electronics" })).toBeInTheDocument();
  });

  it("keeps the citation intact while filtered", () => {
    render(<DisplayPanel chart={chart} sources={[]} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "DE" }));

    expect(screen.getByText("Based on query_003")).toBeInTheDocument();
  });

  it("says when the display holds fewer rows than the query returned", () => {
    render(<DisplayPanel chart={chart} sources={[source]} onClose={vi.fn()} />);

    expect(screen.getByText(/holds 3 of the 4,200 rows/)).toBeInTheDocument();
  });

  it("stays quiet about the population when the display holds it all", () => {
    render(
      <DisplayPanel chart={chart} sources={[{ ...source, row_count: 3 }]} onClose={vi.fn()} />,
    );

    expect(screen.queryByText(/rows the source query returned/)).not.toBeInTheDocument();
  });

  it("explains an empty result instead of showing a blank display", () => {
    render(<DisplayPanel chart={chart} sources={[]} onClose={vi.fn()} />);

    // Electronics is sold in DE only, so pairing it with FR excludes everything.
    fireEvent.click(screen.getByRole("button", { name: "FR" }));
    fireEvent.click(screen.getByRole("button", { name: "Electronics" }));

    expect(screen.getByText("No rows match these filters.")).toBeInTheDocument();
    expect(screen.getByText("Showing 0 of 3 rows")).toBeInTheDocument();
  });

  it("restores the original view on reset", () => {
    render(<DisplayPanel chart={chart} sources={[]} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "FR" }));

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));

    expect(screen.getByText("Showing 3 of 3 rows")).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(<DisplayPanel chart={chart} sources={[]} onClose={onClose} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });
});
