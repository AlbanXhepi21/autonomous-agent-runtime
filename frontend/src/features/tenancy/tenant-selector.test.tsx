import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TenantSelector } from "./tenant-selector";
import { authApi } from "@/lib/api/auth";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import { readLastWorkspaceId } from "@/lib/auth/last-workspace";
import type { Membership, Workspace } from "@/types/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/auth", () => ({ authApi: { logout: vi.fn() } }));
vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { list: vi.fn() },
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
    version: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function membership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: "m1",
    user_id: "user-1",
    workspace_id: "ws-1",
    role: "viewer",
    status: "active",
    invited_by: null,
    joined_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("TenantSelector", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(workspacesApi.list).mockResolvedValue({
      items: [workspace(), workspace({ id: "ws-2", name: "Globex" })],
    });
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [membership()] });
  });

  it("switches to another workspace and remembers the selection", async () => {
    render(
      <TenantSelector
        workspaceId="ws-1"
        workspaceName="Acme"
        userId="user-1"
        userDisplayName="Ada"
        userEmail="ada@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));

    const globex = await screen.findByRole("menuitem", { name: "Globex" });
    fireEvent.click(globex);

    expect(push).toHaveBeenCalledWith("/w/ws-2");
    expect(readLastWorkspaceId()).toBe("ws-2");
  });

  it("cannot switch to a deactivated workspace", async () => {
    vi.mocked(workspacesApi.list).mockResolvedValue({
      items: [workspace(), workspace({ id: "ws-2", name: "Globex", is_active: false })],
    });
    render(
      <TenantSelector
        workspaceId="ws-1"
        workspaceName="Acme"
        userId="user-1"
        userDisplayName="Ada"
        userEmail="ada@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));

    const globex = await screen.findByRole("menuitem", { name: /Globex/ });
    expect(globex).toBeDisabled();
    expect(push).not.toHaveBeenCalled();
  });

  it("signs out and sends the caller to login", async () => {
    vi.mocked(authApi.logout).mockResolvedValue({ message: "Signed out." });
    render(
      <TenantSelector
        workspaceId="ws-1"
        workspaceName="Acme"
        userId="user-1"
        userDisplayName="Ada"
        userEmail="ada@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));

    fireEvent.click(await screen.findByRole("menuitem", { name: "Sign out" }));

    await waitFor(() => expect(authApi.logout).toHaveBeenCalled());
    expect(push).toHaveBeenCalledWith("/login");
  });

  it("shows the organization settings link only for an owner or admin", async () => {
    vi.mocked(membershipsApi.list).mockResolvedValue({
      items: [membership({ role: "admin" })],
    });
    render(
      <TenantSelector
        workspaceId="ws-1"
        workspaceName="Acme"
        userId="user-1"
        userDisplayName="Ada"
        userEmail="ada@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));

    expect(
      await screen.findByRole("menuitem", { name: "Organization settings" }),
    ).toBeInTheDocument();
  });

  it("hides the organization settings link for a viewer", async () => {
    render(
      <TenantSelector
        workspaceId="ws-1"
        workspaceName="Acme"
        userId="user-1"
        userDisplayName="Ada"
        userEmail="ada@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));

    await screen.findByRole("menuitem", { name: "Globex" });
    expect(
      screen.queryByRole("menuitem", { name: "Organization settings" }),
    ).not.toBeInTheDocument();
  });

  it("closes the menu on Escape", async () => {
    render(
      <TenantSelector
        workspaceId="ws-1"
        workspaceName="Acme"
        userId="user-1"
        userDisplayName="Ada"
        userEmail="ada@example.com"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Acme/ }));
    await screen.findByRole("menu");

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
  });
});
