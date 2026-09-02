import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SavedReportsPanel } from "./saved-reports-panel";
import { savedReportsApi } from "@/lib/api/saved-reports";
import type { SavedReportSummary } from "@/types/saved-reports";

vi.mock("@/lib/api/saved-reports", () => ({
  savedReportsApi: {
    list: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    archive: vi.fn(),
    resolvedParameters: vi.fn(),
    execute: vi.fn(),
    executions: vi.fn(),
  },
}));

function summary(overrides: Partial<SavedReportSummary> = {}): SavedReportSummary {
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
    ...overrides,
  };
}

describe("SavedReportsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(savedReportsApi.list).mockResolvedValue({ items: [summary()], total: 1, limit: 10, offset: 0 });
    vi.mocked(savedReportsApi.get).mockResolvedValue({
      ...summary(),
      metric_requests: [{ metric: "revenue", dimensions: [], filters: [], grain: "month" }],
      default_period: { kind: "last_n_days", days: 30, start: null, end: null },
      seed_run_id: null,
      seed_narrative: null,
      seed_narrative_period: null,
    });
    vi.mocked(savedReportsApi.resolvedParameters).mockResolvedValue({
      resolved_period_start: "2026-01-01",
      resolved_period_end: "2026-01-31",
      resolved_period_description: "last 30 complete day(s)",
      metric_requests: [{ metric: "revenue", dimensions: [], filters: [], grain: "month" }],
      pinned_template_version: "4",
      current_template_version: "4",
      template_version_matches_pin: true,
    });
    vi.mocked(savedReportsApi.executions).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
  });

  it("lists saved reports once loaded", async () => {
    render(<SavedReportsPanel />);

    expect(await screen.findByText("Weekly Revenue")).toBeInTheDocument();
    expect(screen.getByText("Saved Reports")).toBeInTheDocument();
    expect(screen.getByText("(1)")).toBeInTheDocument();
  });

  it("says when there are none, rather than showing an empty list silently", async () => {
    vi.mocked(savedReportsApi.list).mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });
    render(<SavedReportsPanel />);

    expect(await screen.findByText("No saved reports yet.")).toBeInTheDocument();
  });

  it("switching to Archived asks the API for archived reports", async () => {
    render(<SavedReportsPanel />);
    await screen.findByText("Weekly Revenue");

    fireEvent.click(screen.getByRole("button", { name: "Archived" }));

    await waitFor(() => expect(savedReportsApi.list).toHaveBeenCalledWith("archived", 10, 0));
  });

  it("selecting an item opens its detail panel", async () => {
    render(<SavedReportsPanel />);
    await screen.findByText("Weekly Revenue");

    fireEvent.click(screen.getByRole("button", { name: "Weekly Revenue" }));

    await waitFor(() => expect(savedReportsApi.get).toHaveBeenCalledWith("report-1"));
    expect(await screen.findAllByText("Weekly Revenue")).toHaveLength(2);
  });

  it("closing the detail panel returns to just the list", async () => {
    render(<SavedReportsPanel />);
    await screen.findByText("Weekly Revenue");
    fireEvent.click(screen.getByRole("button", { name: "Weekly Revenue" }));
    await screen.findByLabelText("Saved report: Weekly Revenue");

    fireEvent.click(screen.getByRole("button", { name: "Close saved report" }));

    await waitFor(() =>
      expect(screen.queryByLabelText("Saved report: Weekly Revenue")).not.toBeInTheDocument(),
    );
  });

  it("re-fetches the list whenever refreshKey changes", async () => {
    const { rerender } = render(<SavedReportsPanel refreshKey="0" />);
    await waitFor(() => expect(savedReportsApi.list).toHaveBeenCalledTimes(1));

    rerender(<SavedReportsPanel refreshKey="1" />);

    await waitFor(() => expect(savedReportsApi.list).toHaveBeenCalledTimes(2));
  });
});
