import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DangerZone } from "./danger-zone";
import { SettingsProvider } from "./settings-context";
import { SettingsLoadedGate } from "./test-support";
import { ApiError } from "@/lib/api/client";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { Membership, Workspace } from "@/types/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn(), leave: vi.fn(), transferOwnership: vi.fn(), deactivate: vi.fn() },
  membershipsApi: { list: vi.fn() },
}));

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

function member(overrides: Partial<Membership> = {}): Membership {
  return {
    id: "m1",
    user_id: "u1",
    workspace_id: "ws-1",
    role: "owner",
    status: "active",
    invited_by: null,
    joined_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderWith(members: Membership[]) {
  vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
  vi.mocked(membershipsApi.list).mockResolvedValue({ items: members });
  return render(
    <SettingsProvider
      workspaceId="ws-1"
      currentUserId="u1"
      currentUserDisplayName="Ada"
      currentUserEmail="a@example.com"
    >
      <SettingsLoadedGate>
        <DangerZone />
      </SettingsLoadedGate>
    </SettingsProvider>,
  );
}

describe("DangerZone", () => {
  beforeEach(() => vi.resetAllMocks());

  it("blocks the sole owner from leaving and explains why", async () => {
    renderWith([member({ user_id: "u1", role: "owner" })]);

    const leaveButton = await screen.findByRole("button", { name: "Leave organization" });
    expect(leaveButton).toBeDisabled();
    expect(screen.getByText(/only owner of this organization/)).toBeInTheDocument();
  });

  it("lets a non-owner leave after confirming", async () => {
    vi.mocked(workspacesApi.leave).mockResolvedValue({ message: "You have left the workspace." });
    renderWith([
      member({ user_id: "u1", role: "viewer" }),
      member({ id: "m2", user_id: "u2", role: "owner" }),
    ]);

    fireEvent.click(await screen.findByRole("button", { name: "Leave organization" }));
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Leave organization" }));

    await waitFor(() => expect(workspacesApi.leave).toHaveBeenCalledWith("ws-1"));
    expect(push).toHaveBeenCalledWith("/");
  });

  it("surfaces the backend's last-owner error if it still occurs", async () => {
    vi.mocked(workspacesApi.leave).mockRejectedValue(
      new ApiError("The last owner cannot leave the workspace.", 409, "last_owner"),
    );
    renderWith([
      member({ user_id: "u1", role: "viewer" }),
      member({ id: "m2", user_id: "u2", role: "owner" }),
    ]);

    fireEvent.click(await screen.findByRole("button", { name: "Leave organization" }));
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Leave organization" }));

    expect(
      await within(dialog).findByText(/transfer ownership before leaving/),
    ).toBeInTheDocument();
  });

  it("only offers transfer ownership and deactivate to an owner", async () => {
    renderWith([
      member({ user_id: "u1", role: "admin" }),
      member({ id: "m2", user_id: "u2", role: "owner" }),
    ]);

    await screen.findByRole("button", { name: "Leave organization" });
    expect(screen.queryByText("Transfer ownership")).not.toBeInTheDocument();
    expect(screen.queryByText("Deactivate organization")).not.toBeInTheDocument();
  });

  it("transfers ownership to the selected active member", async () => {
    vi.mocked(workspacesApi.transferOwnership).mockResolvedValue(
      member({ id: "m2", user_id: "u2", role: "owner" }),
    );
    renderWith([
      member({ user_id: "u1", role: "owner" }),
      member({ id: "m2", user_id: "u2", role: "admin" }),
    ]);

    fireEvent.click(await screen.findByRole("button", { name: "Transfer ownership" }));
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Transfer ownership" }));

    await waitFor(() =>
      expect(workspacesApi.transferOwnership).toHaveBeenCalledWith("ws-1", { to_user_id: "u2" }),
    );
  });

  it("requires typing the organization name to deactivate", async () => {
    renderWith([member({ user_id: "u1", role: "owner" })]);

    fireEvent.click(await screen.findByRole("button", { name: "Deactivate organization" }));
    const dialog = await screen.findByRole("alertdialog");
    const confirmButton = within(dialog).getByRole("button", { name: "Deactivate organization" });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/Type/), { target: { value: "Acme" } });
    expect(confirmButton).not.toBeDisabled();
    expect(workspacesApi.deactivate).not.toHaveBeenCalled();
  });
});
