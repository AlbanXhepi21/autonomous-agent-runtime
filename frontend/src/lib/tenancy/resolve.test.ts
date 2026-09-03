import { describe, expect, it } from "vitest";
import { classifyWorkspaceAccess, resolveTenantLanding } from "./resolve";
import type { Workspace } from "@/types/api";

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

describe("resolveTenantLanding", () => {
  it("shows onboarding when the caller has no workspace", () => {
    expect(resolveTenantLanding([], undefined)).toEqual({ action: "onboarding" });
  });

  it("auto-opens the only active workspace", () => {
    const only = workspace();
    expect(resolveTenantLanding([only], undefined)).toEqual({
      action: "redirect",
      workspaceId: only.id,
    });
  });

  it("explains a single deactivated workspace instead of opening it", () => {
    const only = workspace({ is_active: false });
    expect(resolveTenantLanding([only], undefined)).toEqual({
      action: "disabled",
      workspace: only,
    });
  });

  it("restores the remembered workspace among several", () => {
    const remembered = workspace({ id: "ws-2", name: "Globex" });
    const workspaces = [workspace(), remembered];
    expect(resolveTenantLanding(workspaces, remembered.id)).toEqual({
      action: "redirect",
      workspaceId: remembered.id,
    });
  });

  it("shows the chooser among several with no remembered workspace", () => {
    const workspaces = [workspace(), workspace({ id: "ws-2", name: "Globex" })];
    expect(resolveTenantLanding(workspaces, undefined)).toEqual({
      action: "chooser",
      workspaces,
      discardStale: false,
    });
  });

  it("discards a remembered id that no longer matches any workspace", () => {
    const workspaces = [workspace(), workspace({ id: "ws-2", name: "Globex" })];
    expect(resolveTenantLanding(workspaces, "ws-removed")).toEqual({
      action: "chooser",
      workspaces,
      discardStale: true,
    });
  });

  it("explains a remembered but deactivated workspace among several", () => {
    const remembered = workspace({ id: "ws-2", name: "Globex", is_active: false });
    const workspaces = [workspace(), remembered];
    expect(resolveTenantLanding(workspaces, remembered.id)).toEqual({
      action: "disabled",
      workspace: remembered,
    });
  });
});

describe("classifyWorkspaceAccess", () => {
  it("is unknown when the caller has no membership record for the workspace at all", () => {
    expect(classifyWorkspaceAccess([], "ws-1", { status: 404, workspace: null })).toEqual({
      kind: "unknown",
    });
  });

  it("recognizes a deactivated tenant even though the per-workspace lookup only 404s", () => {
    const disabled = workspace({ is_active: false });
    expect(
      classifyWorkspaceAccess([disabled], disabled.id, { status: 404, workspace: null }),
    ).toEqual({
      kind: "disabled_tenant",
      workspace: disabled,
    });
  });

  it("recognizes a disabled membership on an otherwise active workspace", () => {
    const active = workspace();
    expect(classifyWorkspaceAccess([active], active.id, { status: 403, workspace: null })).toEqual({
      kind: "membership_disabled",
    });
  });

  it("returns the resolved workspace on a clean lookup", () => {
    const active = workspace();
    expect(
      classifyWorkspaceAccess([active], active.id, { status: 200, workspace: active }),
    ).toEqual({
      kind: "ok",
      workspace: active,
    });
  });
});
