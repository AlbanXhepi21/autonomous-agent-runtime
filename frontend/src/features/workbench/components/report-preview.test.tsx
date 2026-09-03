import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportPreviewPanel } from "./report-preview";
import { analyticsApi } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";
import type { ReportPreview } from "@/types/analytics";
import { WorkspaceIdProvider } from "@/features/workbench/workspace-context";

function withWorkspace(children: ReactNode) {
  return <WorkspaceIdProvider workspaceId="ws-1">{children}</WorkspaceIdProvider>;
}

vi.mock("@/lib/api/analytics", () => ({
  analyticsApi: { previewReport: vi.fn() },
}));

function preview(overrides: Partial<ReportPreview> = {}): ReportPreview {
  return {
    template_name: "executive_dashboard",
    template_title: "Executive Dashboard",
    report: {
      report_id: "r1",
      run_id: "run-1",
      title: "Executive Dashboard",
      template_id: "executive_dashboard",
      template_version: "3",
      subtitle: null,
      analysis_period: null,
      displayed_period: "August 2026",
      narrative_period_status: "current",
      narrative_warning: null,
      orientation: "landscape",
      blocks: [
        { kind: "cover", heading: null, title: "Executive Dashboard", subtitle: null, period: "August 2026", generated_at: "2026-01-01T00:00:00Z" },
        {
          kind: "metrics", heading: "Headline Metrics",
          metrics: [
            { label: "Total failures", display_value: "120", change: null, raw_value: 120, source_query_ids: ["query_001"], source_column: null, row_selector: null },
          ],
          empty_message: "",
        },
        {
          kind: "chart", heading: "Charts", chart_id: "c-breakdown", title: "Failures by method", figure_label: "Figure 1",
          chart_type: "bar", caption: null, source_query_ids: ["query_002"],
          data: { columns: [], rows: [], total_row_count: null },
          formatting: { currency: null, decimal_places: null, show_legend: true }, period: "August 2026",
        },
        {
          kind: "caveats", heading: "Limitations", stated: ["Sample limited to card payments."], system_notices: [], empty_message: "",
        },
      ],
      sources: [
        { id: "query_001", kind: "database_query", run_id: "run-1", label: "Total failures", referenced_tables: ["payments"], columns: [], row_count: 1, truncated: false, executed_at: null, metric: null, dimensions: [], filters: [], sql_fingerprint: null },
      ],
      generated_at: "2026-01-01T00:00:00Z",
    },
    suitability: {
      template_name: "executive_dashboard", completion_percentage: 50,
      satisfied_required_slots: ["primary_breakdown"], missing_required_slots: ["headline_metrics"],
      optional_slots_filled: 0, optional_slots_total: 2, unused_display_count: 0, warnings: [], can_publish: false,
    },
    assignment: {
      template_name: "executive_dashboard",
      slots: [
        { slot_id: "headline_metrics", accepts: ["kpi"], block_kind: "metrics", role: "primary", required: true, minimum: 3, maximum: 6, assigned_chart_ids: [], satisfied: false },
        { slot_id: "primary_breakdown", accepts: ["bar", "stacked_bar"], block_kind: "chart", role: "primary", required: true, minimum: 1, maximum: 1, assigned_chart_ids: ["c-breakdown"], satisfied: true },
      ],
      unused_chart_ids: [],
      unresolved_evidence_chart_ids: [],
    },
    missing_required_content: ["'headline_metrics' needs at least 3 display(s) of type kpi, but only 0 are available."],
    estimated_page_count: 3,
    pdf_authoritative_notice: "This preview is generated for review only. The published PDF is authoritative.",
    ...overrides,
  };
}

describe("ReportPreviewPanel", () => {
  beforeEach(() => {
    vi.mocked(analyticsApi.previewReport).mockReset();
  });

  it("renders nothing when no template is selected", () => {
    const { container } = render(
      withWorkspace(
        <ReportPreviewPanel runId="run-1" template="" period="" metrics={[]} narrative="current" />,
      ),
    );

    expect(container).toBeEmptyDOMElement();
    expect(analyticsApi.previewReport).not.toHaveBeenCalled();
  });

  it("shows the suitability score, missing content, and assigned displays", async () => {
    vi.mocked(analyticsApi.previewReport).mockResolvedValue(preview());

    render(
      withWorkspace(
        <ReportPreviewPanel
          runId="run-1"
          template="executive_dashboard"
          period=""
          metrics={[]}
          narrative="current"
        />,
      ),
    );

    expect(await screen.findByText("50% complete")).toBeInTheDocument();
    expect(screen.getByText(/needs at least 3 display/)).toBeInTheDocument();
    expect(screen.getByText("Failures by method")).toBeInTheDocument();
    expect(screen.getByText("Limitations")).toBeInTheDocument();
    expect(screen.getByText("Sample limited to card payments.")).toBeInTheDocument();
    expect(screen.getByText(/authoritative/)).toBeInTheDocument();
    expect(screen.getByText(/~3 pages/)).toBeInTheDocument();
  });

  it("shows no missing-content warning once every required slot is satisfied", async () => {
    vi.mocked(analyticsApi.previewReport).mockResolvedValue(
      preview({
        suitability: {
          template_name: "executive_dashboard", completion_percentage: 100,
          satisfied_required_slots: ["headline_metrics", "primary_breakdown"], missing_required_slots: [],
          optional_slots_filled: 0, optional_slots_total: 2, unused_display_count: 0, warnings: [], can_publish: true,
        },
        missing_required_content: [],
      }),
    );

    render(
      withWorkspace(
        <ReportPreviewPanel
          runId="run-1"
          template="executive_dashboard"
          period=""
          metrics={[]}
          narrative="current"
        />,
      ),
    );

    expect(await screen.findByText("100% complete")).toBeInTheDocument();
    expect(screen.queryByText("Missing required content")).not.toBeInTheDocument();
  });

  it("re-fetches when the selected template changes", async () => {
    vi.mocked(analyticsApi.previewReport).mockResolvedValue(preview());

    const { rerender } = render(
      withWorkspace(
        <ReportPreviewPanel
          runId="run-1"
          template="executive_dashboard"
          period=""
          metrics={[]}
          narrative="current"
        />,
      ),
    );
    await screen.findByText("50% complete");

    rerender(
      withWorkspace(
        <ReportPreviewPanel
          runId="run-1"
          template="analysis_summary"
          period=""
          metrics={[]}
          narrative="current"
        />,
      ),
    );

    await waitFor(() =>
      expect(analyticsApi.previewReport).toHaveBeenLastCalledWith(
        "ws-1",
        "run-1",
        expect.objectContaining({ template: "analysis_summary" }),
      ),
    );
  });

  it("surfaces a preview failure without crashing", async () => {
    vi.mocked(analyticsApi.previewReport).mockRejectedValue(new ApiError("Only a completed run can be previewed."));

    render(
      withWorkspace(
        <ReportPreviewPanel
          runId="run-1"
          template="executive_dashboard"
          period=""
          metrics={[]}
          narrative="current"
        />,
      ),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Only a completed run can be previewed.");
  });
});
