import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportPreferencesSettings } from "./report-preferences-settings";
import { SettingsProvider } from "./settings-context";
import { analyticsApi } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { Membership, ReportPreferences, Workspace } from "@/types/api";

vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn(), getReportPreferences: vi.fn(), updateReportPreferences: vi.fn() },
  membershipsApi: { list: vi.fn() },
}));
vi.mock("@/lib/api/analytics", () => ({
  analyticsApi: { reportTemplates: vi.fn() },
}));

function preferences(overrides: Partial<ReportPreferences> = {}): ReportPreferences {
  return {
    workspace_id: "ws-1",
    default_template: null,
    default_output_format: "pdf",
    default_theme: null,
    default_narrative_policy: "exclude",
    evidence_appendix_enabled: false,
    technical_sql_appendix_enabled: false,
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function workspace(): Workspace {
  return {
    id: "ws-1",
    name: "Acme",
    slug: "acme",
    logo_ref: null,
    is_active: true,
    default_timezone: "UTC",
    default_locale: "en-US",
    default_currency: "USD",
    fiscal_year_start_month: 1,
    number_format: "1,234.56",
    date_format: "YYYY-MM-DD",
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function membership(role: Membership["role"]): Membership {
  return {
    id: "m1",
    user_id: "u1",
    workspace_id: "ws-1",
    role,
    status: "active",
    invited_by: null,
    joined_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function renderAs(role: Membership["role"]) {
  vi.mocked(membershipsApi.list).mockResolvedValue({ items: [membership(role)] });
  return render(
    <SettingsProvider
      workspaceId="ws-1"
      currentUserId="u1"
      currentUserDisplayName="Ada"
      currentUserEmail="a@example.com"
    >
      <ReportPreferencesSettings />
    </SettingsProvider>,
  );
}

describe("ReportPreferencesSettings", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
    vi.mocked(analyticsApi.reportTemplates).mockResolvedValue({
      items: [
        {
          name: "analysis_summary",
          title: "Analysis Summary",
          description: "",
          report_type: "",
          period_granularity: "month",
          sections: [],
        },
      ],
    });
  });

  it("shows a loading state before preferences resolve", () => {
    vi.mocked(workspacesApi.getReportPreferences).mockImplementation(() => new Promise(() => {}));
    renderAs("admin");

    expect(screen.getByText("Loading report preferences…")).toBeInTheDocument();
  });

  it("shows an error instead of a broken form when preferences fail to load", async () => {
    vi.mocked(workspacesApi.getReportPreferences).mockRejectedValue(
      new ApiError("Preferences unavailable.", 500),
    );
    renderAs("admin");

    expect(await screen.findByRole("alert")).toHaveTextContent("Preferences unavailable.");
  });

  it("populates the template select from the reports API, not a hardcoded list", async () => {
    vi.mocked(workspacesApi.getReportPreferences).mockResolvedValue(preferences());
    renderAs("admin");

    expect(await screen.findByRole("option", { name: "Analysis Summary" })).toBeInTheDocument();
  });

  it("is read-only for an analyst", async () => {
    vi.mocked(workspacesApi.getReportPreferences).mockResolvedValue(preferences());
    renderAs("analyst");

    expect(await screen.findByLabelText("Default format")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();
  });

  it("saves narrative policy and appendix toggles", async () => {
    vi.mocked(workspacesApi.getReportPreferences).mockResolvedValue(preferences());
    vi.mocked(workspacesApi.updateReportPreferences).mockResolvedValue(
      preferences({
        default_narrative_policy: "include_original",
        evidence_appendix_enabled: true,
        version: 2,
      }),
    );
    renderAs("owner");

    fireEvent.click(await screen.findByRole("radio", { name: /Include original narrative/ }));
    fireEvent.click(screen.getByLabelText("Evidence appendix enabled by default"));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(workspacesApi.updateReportPreferences).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({
          default_narrative_policy: "include_original",
          evidence_appendix_enabled: true,
          expected_version: 1,
        }),
      ),
    );
  });
});
