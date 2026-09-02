import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSavedReports } from "./use-saved-reports";
import { savedReportsApi } from "@/lib/api/saved-reports";
import { ApiError } from "@/lib/api/client";
import type { SavedReport, SavedReportSummary } from "@/types/saved-reports";

vi.mock("@/lib/api/saved-reports", () => ({
  savedReportsApi: {
    create: vi.fn(),
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

function detail(overrides: Partial<SavedReport> = {}): SavedReport {
  return {
    ...summary(),
    metric_requests: [{ metric: "revenue", dimensions: [], filters: [], grain: "month" }],
    default_period: { kind: "last_n_days", days: 30, start: null, end: null },
    seed_run_id: null,
    seed_narrative: null,
    seed_narrative_period: null,
    ...overrides,
  };
}

describe("useSavedReports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(savedReportsApi.list).mockResolvedValue({ items: [summary()], total: 1, limit: 10, offset: 0 });
    vi.mocked(savedReportsApi.get).mockResolvedValue(detail());
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

  it("loads the active list by default", async () => {
    const { result } = renderHook(() => useSavedReports());

    await act(async () => {
      await result.current.load();
    });

    expect(savedReportsApi.list).toHaveBeenCalledWith("active", 10, 0);
    expect(result.current.items).toEqual([summary()]);
    expect(result.current.total).toBe(1);
  });

  it("reports a failure instead of a silent no-op when listing fails", async () => {
    vi.mocked(savedReportsApi.list).mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useSavedReports());

    await act(async () => {
      await result.current.load();
    });

    expect(result.current.error).toBe("Saved reports could not be loaded.");
  });

  it("selecting a report fetches its detail, resolved parameters and executions together", async () => {
    const { result } = renderHook(() => useSavedReports());

    await act(async () => {
      await result.current.select("report-1");
    });

    expect(savedReportsApi.get).toHaveBeenCalledWith("report-1");
    expect(savedReportsApi.resolvedParameters).toHaveBeenCalledWith("report-1");
    expect(savedReportsApi.executions).toHaveBeenCalledWith("report-1");
    expect(result.current.detail?.id).toBe("report-1");
    expect(result.current.resolvedParameters?.template_version_matches_pin).toBe(true);
  });

  it("close clears the selection and every piece of loaded detail", async () => {
    const { result } = renderHook(() => useSavedReports());
    await act(async () => {
      await result.current.select("report-1");
    });

    act(() => result.current.close());

    expect(result.current.selectedId).toBeNull();
    expect(result.current.detail).toBeNull();
    expect(result.current.executions).toEqual([]);
  });

  it("create adds the new report to the front of the list", async () => {
    vi.mocked(savedReportsApi.create).mockResolvedValue(detail({ id: "report-2", name: "New One" }));
    const { result } = renderHook(() => useSavedReports());

    await act(async () => {
      await result.current.create({
        workspace_id: "default",
        name: "New One",
        template_id: "analysis_summary",
        metric_requests: [{ metric: "revenue", grain: "month" }],
        default_period: { kind: "current_month" },
        narrative_policy: "exclude",
      });
    });

    expect(result.current.items[0].id).toBe("report-2");
    expect(result.current.total).toBe(1);
  });

  it("update sends the currently selected report's version as expected_version", async () => {
    vi.mocked(savedReportsApi.update).mockResolvedValue(detail({ name: "Renamed", version: 2 }));
    const { result } = renderHook(() => useSavedReports());
    await act(async () => {
      await result.current.select("report-1");
    });

    await act(async () => {
      await result.current.update({ name: "Renamed" });
    });

    expect(savedReportsApi.update).toHaveBeenCalledWith("report-1", {
      expected_version: 1,
      name: "Renamed",
    });
    expect(result.current.detail?.name).toBe("Renamed");
  });

  it("a version conflict on update surfaces a specific, actionable message", async () => {
    vi.mocked(savedReportsApi.update).mockRejectedValue(new ApiError("conflict", 409));
    const { result } = renderHook(() => useSavedReports());
    await act(async () => {
      await result.current.select("report-1");
    });

    await act(async () => {
      await result.current.update({ name: "Renamed" });
    });

    expect(result.current.error).toMatch(/changed elsewhere/);
  });

  it("archive removes the report from the list and clears its slot", async () => {
    vi.mocked(savedReportsApi.archive).mockResolvedValue(detail({ status: "archived", version: 2 }));
    const { result } = renderHook(() => useSavedReports());
    await act(async () => {
      await result.current.select("report-1");
    });
    result.current.items.push(summary());

    await act(async () => {
      await result.current.archive();
    });

    expect(savedReportsApi.archive).toHaveBeenCalledWith("report-1", { expected_version: 1 });
    expect(result.current.detail?.status).toBe("archived");
  });

  it("execute stores the result and refreshes the execution history", async () => {
    vi.mocked(savedReportsApi.execute).mockResolvedValue({
      execution_id: "exec-1",
      run_id: "saved-report-run-1",
      mode: "preview",
      status: "completed",
      resolved_period_start: "2026-01-01",
      resolved_period_end: "2026-01-31",
      preview: null,
      documents: [],
    });
    vi.mocked(savedReportsApi.executions).mockResolvedValueOnce({
      items: [], total: 0, limit: 20, offset: 0,
    }).mockResolvedValueOnce({
      items: [{
        id: "exec-1", run_id: "saved-report-run-1", mode: "preview", status: "completed",
        resolved_period_start: "2026-01-01", resolved_period_end: "2026-01-31",
        formats: null, error: null, created_at: "2026-01-01T00:00:00Z", completed_at: "2026-01-01T00:00:01Z",
        artifacts: [],
      }],
      total: 1, limit: 20, offset: 0,
    });
    const { result } = renderHook(() => useSavedReports());
    await act(async () => {
      await result.current.select("report-1");
    });

    await act(async () => {
      await result.current.execute("preview");
    });

    expect(savedReportsApi.execute).toHaveBeenCalledWith("report-1", { mode: "preview", formats: ["pdf"] });
    await waitFor(() => expect(result.current.executions).toHaveLength(1));
    expect(result.current.lastResult?.run_id).toBe("saved-report-run-1");
  });

  it("execute without a selected report is a no-op", async () => {
    const { result } = renderHook(() => useSavedReports());

    const outcome = await act(async () => result.current.execute("preview"));

    expect(outcome).toBeNull();
    expect(savedReportsApi.execute).not.toHaveBeenCalled();
  });
});
