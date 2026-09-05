import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TenantSelector } from "./tenant-selector";
import { authApi } from "@/lib/api/auth";
import { workspacesApi } from "@/lib/api/workspaces";
import { readLastWorkspaceId } from "@/lib/auth/last-workspace";
import type { Workspace } from "@/types/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/auth", () => ({ authApi: { logout: vi.fn() } }));
vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { list: vi.fn() },
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

describe("TenantSelector", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(workspacesApi.list).mockResolvedValue({
      items: [workspace(), workspace({ id: "ws-2", name: "Globex" })],
    });
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

  it("always shows a link to the caller's own personal settings", async () => {
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

    const link = await screen.findByRole("menuitem", { name: "User settings" });
    expect(link).toHaveAttribute("href", "/settings/profile");
  });

  it("shows the organization settings link for any active member, not only an owner or admin", async () => {
    // The nav link is not itself a permission boundary -- every settings page
    // it leads to is readable by any member and independently enforces
    // which fields a viewer or analyst may edit. See `settings-nav.tsx` and
    // the backend's `require_permission` checks.
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

    const link = await screen.findByRole("menuitem", { name: "Organization settings" });
    expect(link).toHaveAttribute("href", "/w/ws-1/settings");
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
