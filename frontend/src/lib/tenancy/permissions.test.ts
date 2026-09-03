import { describe, expect, it } from "vitest";
import {
  canDeactivateOrganization,
  canEditOrganization,
  canInviteRole,
  canManageMember,
  canManageMembers,
  canTransferOwnership,
  canViewAuditLog,
} from "./permissions";

describe("canEditOrganization", () => {
  it("permits owner and admin, not analyst or viewer", () => {
    expect(canEditOrganization("owner")).toBe(true);
    expect(canEditOrganization("admin")).toBe(true);
    expect(canEditOrganization("analyst")).toBe(false);
    expect(canEditOrganization("viewer")).toBe(false);
  });
});

describe("canManageMembers / canManageMember", () => {
  it("permits owner and admin to manage members generally", () => {
    expect(canManageMembers("owner")).toBe(true);
    expect(canManageMembers("admin")).toBe(true);
    expect(canManageMembers("analyst")).toBe(false);
    expect(canManageMembers("viewer")).toBe(false);
  });

  it("blocks an admin from managing an owner", () => {
    expect(canManageMember("admin", "owner")).toBe(false);
    expect(canManageMember("admin", "admin")).toBe(true);
    expect(canManageMember("admin", "analyst")).toBe(true);
  });

  it("lets an owner manage anyone, including another owner", () => {
    expect(canManageMember("owner", "owner")).toBe(true);
    expect(canManageMember("owner", "viewer")).toBe(true);
  });

  it("never permits a non-manager regardless of target", () => {
    expect(canManageMember("viewer", "viewer")).toBe(false);
    expect(canManageMember("analyst", "analyst")).toBe(false);
  });
});

describe("canInviteRole", () => {
  it("blocks an admin from inviting a new owner", () => {
    expect(canInviteRole("admin", "owner")).toBe(false);
    expect(canInviteRole("admin", "admin")).toBe(true);
  });

  it("lets an owner invite any role", () => {
    expect(canInviteRole("owner", "owner")).toBe(true);
  });
});

describe("canViewAuditLog", () => {
  it("matches the same gate as editing settings", () => {
    expect(canViewAuditLog("owner")).toBe(true);
    expect(canViewAuditLog("admin")).toBe(true);
    expect(canViewAuditLog("analyst")).toBe(false);
    expect(canViewAuditLog("viewer")).toBe(false);
  });
});

describe("owner-only actions", () => {
  it("restricts transfer and deactivate to owner alone", () => {
    expect(canTransferOwnership("owner")).toBe(true);
    expect(canTransferOwnership("admin")).toBe(false);
    expect(canDeactivateOrganization("owner")).toBe(true);
    expect(canDeactivateOrganization("admin")).toBe(false);
  });
});
