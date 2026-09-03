import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SaveReportForm } from "./save-report-form";
import { savedReportsApi } from "@/lib/api/saved-reports";
import { ApiError } from "@/lib/api/client";
import type { MetricParameters } from "@/types/analytics";
import type { SavedReport } from "@/types/saved-reports";
import { WorkspaceIdProvider } from "@/features/workbench/workspace-context";

vi.mock("@/lib/api/saved-reports", () => ({
  savedReportsApi: { create: vi.fn() },
}));

const METRICS: MetricParameters[] = [
  { metric: "revenue", period: { start: "2026-01-01", end: "2026-02-01" }, grain: "month" },
];

function saved(overrides: Partial<SavedReport> = {}): SavedReport {
  return {
    id: "report-1",
    workspace_id: "default",
    owner: null,
    name: "Weekly Revenue",
    description: null,
    template_id: "analysis_summary",
    template_version: "4",
    narrative_policy: "exclude",
    status: "active",
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    metric_requests: [{ metric: "revenue", dimensions: [], filters: [], grain: "month" }],
    default_period: { kind: "last_n_days", days: 30, start: null, end: null },
    seed_run_id: null,
    seed_narrative: null,
    seed_narrative_period: null,
    ...overrides,
  };
}

describe("SaveReportForm", () => {
  beforeEach(() => {
    vi.mocked(savedReportsApi.create).mockResolvedValue(saved());
  });

  it("explains why saving is unavailable when no metrics have been chosen", () => {
    render(
      <WorkspaceIdProvider workspaceId="ws-1">
        <SaveReportForm runId="run-1" template="analysis_summary" metrics={[]} narrativeText="" />
      </WorkspaceIdProvider>,
    );

    expect(screen.getByText(/Choose one or more metrics to recompute/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save as report…" })).not.toBeInTheDocument();
  });

  const openForm = () => {
    render(
      <WorkspaceIdProvider workspaceId="ws-1">
        <SaveReportForm
          runId="run-1"
          template="analysis_summary"
          metrics={METRICS}
          narrativeText=""
        />
      </WorkspaceIdProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save as report…" }));
  };

  it("cannot save without a name", () => {
    openForm();

    expect(screen.getByRole("button", { name: "Save report" })).toBeDisabled();
  });

  it("saves with the current template, metrics and a relative period", async () => {
    openForm();

    fireEvent.change(screen.getByPlaceholderText("Weekly revenue"), {
      target: { value: "Weekly Revenue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save report" }));

    await waitFor(() =>
      expect(savedReportsApi.create).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({
          name: "Weekly Revenue",
          template_id: "analysis_summary",
          metric_requests: [{ metric: "revenue", dimensions: [], filters: [], grain: "month" }],
          default_period: { kind: "last_n_days", days: 30 },
          narrative_policy: "exclude",
        }),
      ),
    );
    expect(await screen.findByText(/Reopen it from Saved Reports/)).toBeInTheDocument();
  });

  it("switches to a fixed period and sends the chosen dates", async () => {
    openForm();

    fireEvent.change(screen.getByPlaceholderText("Weekly revenue"), { target: { value: "Q1" } });
    fireEvent.change(screen.getByDisplayValue("Last N complete days"), {
      target: { value: "fixed" },
    });
    const [start, end] = screen.getAllByDisplayValue("");
    fireEvent.change(start, { target: { value: "2026-01-01" } });
    fireEvent.change(end, { target: { value: "2026-04-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Save report" }));

    await waitFor(() =>
      expect(savedReportsApi.create).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({
          default_period: { kind: "fixed", start: "2026-01-01", end: "2026-04-01" },
        }),
      ),
    );
  });

  it("only allows reusing the original narrative when there is one to reuse", () => {
    openForm();

    expect(screen.getByRole("radio", { name: /Reuse this analysis's prose/ })).toBeDisabled();
  });

  it("lets a real narrative be seeded once typed", async () => {
    render(
      <WorkspaceIdProvider workspaceId="ws-1">
        <SaveReportForm
          runId="run-1"
          template="analysis_summary"
          metrics={METRICS}
          narrativeText="Revenue grew 18% this period."
        />
      </WorkspaceIdProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save as report…" }));
    fireEvent.change(screen.getByPlaceholderText("Weekly revenue"), { target: { value: "Q1" } });
    fireEvent.click(screen.getByRole("radio", { name: /Reuse this analysis's prose/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save report" }));

    await waitFor(() =>
      expect(savedReportsApi.create).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({
          narrative_policy: "include_original",
          seed_run_id: "run-1",
          seed_narrative: "Revenue grew 18% this period.",
        }),
      ),
    );
  });

  it("reports a failure instead of a silent no-op", async () => {
    vi.mocked(savedReportsApi.create).mockRejectedValue(
      new ApiError("The saved report could not be created."),
    );
    openForm();

    fireEvent.change(screen.getByPlaceholderText("Weekly revenue"), { target: { value: "Q1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The saved report could not be created.",
    );
  });
});
