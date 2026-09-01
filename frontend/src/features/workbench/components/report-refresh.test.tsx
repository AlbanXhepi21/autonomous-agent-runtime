import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportRefresh } from "./report-refresh";
import { analyticsApi } from "@/lib/api/analytics";
import type { MetricParameters } from "@/types/analytics";

vi.mock("@/lib/api/analytics", () => ({
  analyticsApi: { rerunMetrics: vi.fn() },
}));

const metrics = {
  items: [
    {
      name: "revenue",
      display_name: "Revenue",
      description: "Delivered order revenue",
      unit: "USD",
      format: "currency",
      dimensions: ["country", "period", "status"],
      filters: ["campaign_id", "country", "shipping_country"],
      grains: ["day", "week", "month", "quarter", "year"],
      value_columns: ["revenue", "order_count"],
      required_tables: ["orders"],
      caveats: [],
    },
  ],
};

function setup(
  value: MetricParameters[] = [],
  narrative = "excluded_from_refreshed_report" as const,
) {
  const onChange = vi.fn();
  const onNarrativeChange = vi.fn();
  render(
    <ReportRefresh
      value={value}
      narrative={narrative}
      onChange={onChange}
      onNarrativeChange={onNarrativeChange}
    />,
  );
  return { onChange, onNarrativeChange };
}

describe("ReportRefresh", () => {
  beforeEach(() => {
    vi.mocked(analyticsApi.rerunMetrics).mockResolvedValue(metrics);
  });

  it("offers only the metrics and groupings the server declares", async () => {
    setup();

    await screen.findByText("Revenue");
    const groupBy = screen.getByLabelText("Group by") as HTMLSelectElement;
    const offered = [...groupBy.options].map((option) => option.value);
    // Exactly the server's dimensions, plus the no-grouping default.
    expect(offered).toEqual(["", "country", "period", "status"]);
  });

  it("sends a metric name and dates, never a column or an expression", async () => {
    const { onChange } = setup();
    await screen.findByText("Revenue");

    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-04-01" } });
    fireEvent.change(screen.getByLabelText("Group by"), { target: { value: "country" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(onChange).toHaveBeenCalledWith([
      {
        metric: "revenue",
        period: { start: "2026-01-01", end: "2026-04-01" },
        grain: "month",
        dimensions: ["country"],
      },
    ]);
  });

  it("cannot add a period that ends before it starts", async () => {
    setup();
    await screen.findByText("Revenue");

    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-04-01" } });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-01-01" } });

    expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
  });

  it("offers a bucket only when grouping by period", async () => {
    setup();
    await screen.findByText("Revenue");

    expect(screen.queryByLabelText("Bucket")).toBeNull();
    fireEvent.change(screen.getByLabelText("Group by"), { target: { value: "period" } });
    await waitFor(() => expect(screen.getByLabelText("Bucket")).toBeInTheDocument());
  });

  it("offers both narrative choices and no third option that reuses prose", async () => {
    setup([
      { metric: "revenue", period: { start: "2026-01-01", end: "2026-04-01" }, grain: "month" },
    ]);
    await screen.findByText("Revenue");

    const choices = screen.getAllByRole("radio");
    expect(choices).toHaveLength(2);
    expect(screen.getByText(/Leave it out/)).toBeInTheDocument();
    expect(screen.getByText(/visible warning/)).toBeInTheDocument();
    // The third route is a new investigation, and is described as one.
    expect(screen.getByText(/ask a new question/)).toBeInTheDocument();
  });

  it("says nothing at all when the server offers no recomputable metrics", async () => {
    vi.mocked(analyticsApi.rerunMetrics).mockResolvedValue({ items: [] });

    const { container } = render(
      <ReportRefresh
        value={[]}
        narrative="excluded_from_refreshed_report"
        onChange={vi.fn()}
        onNarrativeChange={vi.fn()}
      />,
    );

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
