import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RegionalSettings } from "./regional-settings";
import { SettingsProvider } from "./settings-context";
import { SettingsLoadedGate } from "./test-support";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { Membership, Workspace } from "@/types/api";

vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn(), update: vi.fn() },
  membershipsApi: { list: vi.fn() },
}));

function workspace(overrides: Partial<Workspace> = {}): Workspace {
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
    version: 2,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
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
  vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
  vi.mocked(membershipsApi.list).mockResolvedValue({ items: [membership(role)] });
  return render(
    <SettingsProvider
      workspaceId="ws-1"
      currentUserId="u1"
      currentUserDisplayName="Ada"
      currentUserEmail="a@example.com"
    >
      <SettingsLoadedGate>
        <RegionalSettings />
      </SettingsLoadedGate>
    </SettingsProvider>,
  );
}

describe("RegionalSettings", () => {
  beforeEach(() => vi.resetAllMocks());

  it("is read-only for a viewer", async () => {
    renderAs("viewer");

    expect(await screen.findByLabelText("Timezone")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();
  });

  it("uppercases a currency code as it's typed", async () => {
    renderAs("admin");

    const currency = await screen.findByLabelText("Currency");
    fireEvent.change(currency, { target: { value: "eur" } });

    expect(currency).toHaveValue("EUR");
  });

  it("saves the regional defaults an admin chooses, without altering already-published data", async () => {
    vi.mocked(workspacesApi.update).mockResolvedValue(
      workspace({ default_currency: "EUR", fiscal_year_start_month: 4, version: 3 }),
    );
    renderAs("admin");

    fireEvent.change(await screen.findByLabelText("Currency"), { target: { value: "EUR" } });
    fireEvent.change(screen.getByLabelText("Fiscal year starts"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(workspacesApi.update).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({
          default_currency: "EUR",
          fiscal_year_start_month: 4,
          expected_version: 2,
        }),
      ),
    );
    // Saving regional formatting is presentation only -- it must never be
    // framed as rewriting a fact, and the page says so.
    expect(screen.getByText(/never rewrites a value already stated/)).toBeInTheDocument();
  });

  it("explains that there is no workspace-wide default report period", async () => {
    renderAs("owner");

    expect(
      await screen.findByText(/isn.t an organization-wide default period/),
    ).toBeInTheDocument();
  });
});
