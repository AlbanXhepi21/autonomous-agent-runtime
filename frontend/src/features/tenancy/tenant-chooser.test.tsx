import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TenantChooser } from "./tenant-chooser";
import {
  forgetLastWorkspaceId,
  readLastWorkspaceId,
  rememberWorkspaceId,
} from "@/lib/auth/last-workspace";
import type { Workspace } from "@/types/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

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

describe("TenantChooser", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forgetLastWorkspaceId();
  });

  it("lists every workspace and lets the caller open an active one", () => {
    const workspaces = [workspace(), workspace({ id: "ws-2", name: "Globex" })];
    render(<TenantChooser workspaces={workspaces} discardStaleSelection={false} />);

    fireEvent.click(screen.getByRole("button", { name: "Globex" }));

    expect(push).toHaveBeenCalledWith("/w/ws-2");
    expect(readLastWorkspaceId()).toBe("ws-2");
  });

  it("disables a deactivated workspace so it cannot be opened", () => {
    const workspaces = [workspace(), workspace({ id: "ws-2", name: "Globex", is_active: false })];
    render(<TenantChooser workspaces={workspaces} discardStaleSelection={false} />);

    const disabledOption = screen.getByRole("button", { name: /Globex/ });
    expect(disabledOption).toBeDisabled();
    fireEvent.click(disabledOption);
    expect(push).not.toHaveBeenCalled();
  });

  it("discards a stale remembered selection on mount", () => {
    rememberWorkspaceId("ws-removed");
    const workspaces = [workspace(), workspace({ id: "ws-2", name: "Globex" })];

    render(<TenantChooser workspaces={workspaces} discardStaleSelection />);

    expect(readLastWorkspaceId()).toBeNull();
  });
});
