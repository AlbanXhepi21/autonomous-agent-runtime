import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DisabledTenantNotice } from "./disabled-tenant-notice";
import { MembershipDisabledNotice } from "./membership-disabled-notice";
import { NoTenantOnboarding } from "./no-tenant-onboarding";
import { readLastWorkspaceId, rememberWorkspaceId } from "@/lib/auth/last-workspace";
import type { Workspace } from "@/types/api";

function workspace(overrides: Partial<Workspace> = {}): Workspace {
  return {
    id: "ws-1",
    name: "Acme",
    slug: "acme",
    logo_ref: null,
    is_active: false,
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

describe("DisabledTenantNotice", () => {
  it("names the deactivated organization and offers a safe way out, without exposing internal detail", () => {
    render(<DisabledTenantNotice workspace={workspace()} />);

    expect(screen.getByRole("heading", { name: "Acme is deactivated" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to your workspaces" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});

describe("MembershipDisabledNotice", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    rememberWorkspaceId("ws-1");
  });

  it("explains the disabled membership and discards the remembered selection", () => {
    render(<MembershipDisabledNotice />);

    expect(screen.getByRole("heading", { name: "Access disabled" })).toBeInTheDocument();
    expect(readLastWorkspaceId()).toBeNull();
  });
});

describe("NoTenantOnboarding", () => {
  it("offers to create an organization", () => {
    render(<NoTenantOnboarding />);

    expect(screen.getByRole("link", { name: "Create an organization" })).toHaveAttribute(
      "href",
      "/organizations/new",
    );
  });
});
