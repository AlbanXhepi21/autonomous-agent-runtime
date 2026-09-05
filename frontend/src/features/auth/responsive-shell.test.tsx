import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthCard } from "@/components/ui/auth-card";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";
import { SettingsShell } from "@/features/settings/settings-shell";

vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: () => new Promise(() => {}) },
  membershipsApi: { list: () => new Promise(() => {}) },
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/w/ws-1/settings/organization" }));

/**
 * jsdom doesn't evaluate CSS, so this isn't a visual regression check --
 * it pins the structural classNames `globals.css` keys its narrow-viewport
 * rules off (`.auth-shell`/`.tenant-state-shell` centering panels that
 * collapse to full width under the `max-width: 760px` breakpoint), so a
 * class rename here would silently break responsive layout without any
 * other test catching it.
 */
describe("responsive shell structure", () => {
  it("wraps an auth page in the centered, width-capped auth-shell", () => {
    render(
      <AuthCard eyebrow="Data Analyst" title="Sign in">
        <p>content</p>
      </AuthCard>,
    );

    const shell = screen.getByText("content").closest(".auth-shell");
    expect(shell).not.toBeNull();
    expect(shell?.querySelector(".auth-card")).not.toBeNull();
  });

  it("wraps a tenant state page in the same responsive shell pattern", () => {
    render(<TenantStateCard title="Choose a workspace">content</TenantStateCard>);

    const shell = screen.getByText("content").closest(".tenant-state-shell");
    expect(shell).not.toBeNull();
    expect(shell?.querySelector(".tenant-state-card")).not.toBeNull();
  });

  it("gives the settings area a two-pane shell that collapses under settings-body/settings-nav", () => {
    render(
      <SettingsShell
        workspaceId="ws-1"
        workspaceName="Acme Analytics"
        currentUserId="u1"
        currentUserDisplayName="Ada"
        currentUserEmail="a@example.com"
      >
        <p>page content</p>
      </SettingsShell>,
    );

    const shell = document.querySelector(".settings-shell");
    expect(shell).not.toBeNull();
    expect(shell?.querySelector(".settings-body")).not.toBeNull();
    expect(shell?.querySelector(".settings-nav")).not.toBeNull();
    expect(shell?.querySelector(".settings-content")).not.toBeNull();
  });
});
