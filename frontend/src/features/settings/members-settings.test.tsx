import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MembersSettings } from "./members-settings";
import { SettingsProvider } from "./settings-context";
import { SettingsLoadedGate } from "./test-support";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { Membership, Workspace } from "@/types/api";

vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn() },
  membershipsApi: { list: vi.fn(), invite: vi.fn(), changeRole: vi.fn(), remove: vi.fn() },
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
        <MembersSettings />
      </SettingsLoadedGate>
    </SettingsProvider>,
  );
}

describe("MembersSettings", () => {
  beforeEach(() => vi.resetAllMocks());

  it("lists members with role, status, and joined date", async () => {
    renderWith([
      member({ user_id: "u1", role: "owner" }),
      member({ id: "m2", user_id: "u2", role: "viewer", status: "disabled" }),
    ]);

    expect(await screen.findByText("Ada (you)")).toBeInTheDocument();
    expect(screen.getByText(/Member u2/)).toBeInTheDocument();
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
  });

  it("hides management actions for a viewer", async () => {
    renderWith([
      member({ user_id: "u1", role: "viewer" }),
      member({ id: "m2", user_id: "u2", role: "analyst" }),
    ]);

    await screen.findByText("Ada (you)");
    expect(screen.queryByRole("button", { name: "Invite member" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Actions" })).not.toBeInTheDocument();
  });

  it("invites a new member with the chosen role", async () => {
    vi.mocked(membershipsApi.invite).mockResolvedValue({
      id: "inv-1",
      workspace_id: "ws-1",
      email: "grace@example.com",
      role: "analyst",
      invited_by: "u1",
      created_at: "2026-01-01T00:00:00Z",
      expires_at: "2026-01-08T00:00:00Z",
      accepted_at: null,
      revoked_at: null,
    });
    renderWith([member({ user_id: "u1", role: "admin" })]);

    fireEvent.click(await screen.findByRole("button", { name: "Invite member" }));
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "grace@example.com" } });
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "analyst" } });
    fireEvent.click(screen.getByRole("button", { name: "Send invitation" }));

    await waitFor(() =>
      expect(membershipsApi.invite).toHaveBeenCalledWith("ws-1", {
        email: "grace@example.com",
        role: "analyst",
      }),
    );
    expect(await screen.findByText("Invitation sent to grace@example.com.")).toBeInTheDocument();
  });

  it("changes another member's role", async () => {
    vi.mocked(membershipsApi.changeRole).mockResolvedValue(
      member({ id: "m2", user_id: "u2", role: "admin" }),
    );
    renderWith([
      member({ user_id: "u1", role: "owner" }),
      member({ id: "m2", user_id: "u2", role: "viewer" }),
    ]);

    await screen.findByText(/Member u2/);
    fireEvent.click(screen.getByRole("button", { name: "Change role" }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "admin" } });

    await waitFor(() =>
      expect(membershipsApi.changeRole).toHaveBeenCalledWith("ws-1", "u2", { role: "admin" }),
    );
  });

  it("requires confirmation before removing a member", async () => {
    vi.mocked(membershipsApi.remove).mockResolvedValue(member({ id: "m2", user_id: "u2" }));
    renderWith([
      member({ user_id: "u1", role: "owner" }),
      member({ id: "m2", user_id: "u2", role: "viewer" }),
    ]);

    await screen.findByText(/Member u2/);
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(membershipsApi.remove).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Remove member" }));

    await waitFor(() => expect(membershipsApi.remove).toHaveBeenCalledWith("ws-1", "u2"));
  });

  it("prevents an admin from managing an owner", async () => {
    renderWith([
      member({ user_id: "u1", role: "admin" }),
      member({ id: "m2", user_id: "u2", role: "owner" }),
    ]);

    await screen.findByText(/Member u2/);
    expect(screen.getByText("Owner-only")).toBeInTheDocument();
  });
});
