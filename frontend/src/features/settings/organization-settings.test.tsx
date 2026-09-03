import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OrganizationSettings } from "./organization-settings";
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
    version: 3,
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

function renderAs(role: Membership["role"], workspaceOverrides: Partial<Workspace> = {}) {
  vi.mocked(workspacesApi.get).mockResolvedValue(workspace(workspaceOverrides));
  vi.mocked(membershipsApi.list).mockResolvedValue({ items: [membership(role)] });
  return render(
    <SettingsProvider
      workspaceId="ws-1"
      currentUserId="u1"
      currentUserDisplayName="Ada"
      currentUserEmail="a@example.com"
    >
      <SettingsLoadedGate>
        <OrganizationSettings />
      </SettingsLoadedGate>
    </SettingsProvider>,
  );
}

describe("OrganizationSettings permission-based controls", () => {
  beforeEach(() => vi.resetAllMocks());

  it("disables every field and hides the save button for a viewer", async () => {
    renderAs("viewer");

    const nameInput = await screen.findByLabelText("Organization name");
    expect(nameInput).toBeDisabled();
    expect(screen.getByLabelText("Timezone")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();
    expect(screen.getByText(/Read-only/)).toBeInTheDocument();
  });

  it("disables every field for an analyst too", async () => {
    renderAs("analyst");

    expect(await screen.findByLabelText("Organization name")).toBeDisabled();
  });

  it("lets an admin edit and save organization settings", async () => {
    vi.mocked(workspacesApi.update).mockResolvedValue(workspace({ name: "Acme Corp", version: 4 }));
    renderAs("admin");

    const nameInput = await screen.findByLabelText("Organization name");
    expect(nameInput).not.toBeDisabled();
    expect(nameInput).toHaveValue("Acme");
    fireEvent.change(nameInput, { target: { value: "Acme Corp" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(workspacesApi.update).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({ name: "Acme Corp", expected_version: 3 }),
      ),
    );
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("always shows the slug as read-only, even for an owner", async () => {
    renderAs("owner");

    expect(await screen.findByLabelText("Slug")).toBeDisabled();
    expect(screen.getByLabelText("Slug")).toHaveValue("acme");
  });
});
