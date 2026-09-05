import type { Role } from "@/types/api";

/**
 * A UX-only mirror of `app.tenancy.permissions.ROLE_PERMISSIONS` and the
 * additional owner-only checks each route layers on top of it
 * (`OwnerRequiredError` on deactivate/transfer, `AdminCannotManageOwnerError`
 * on member management). Nothing here is a security boundary -- every
 * mutation this gates is independently enforced server-side by
 * `require_permission(...)` and the service-layer checks; this exists only
 * so the UI doesn't offer a control the backend would refuse.
 */

export function canEditOrganization(role: Role): boolean {
  return role === "owner" || role === "admin";
}

export function canManageMembers(role: Role): boolean {
  return role === "owner" || role === "admin";
}

/** An admin may manage anyone but an owner; an owner may manage anyone. */
export function canManageMember(actingRole: Role, targetRole: Role): boolean {
  if (!canManageMembers(actingRole)) return false;
  if (actingRole === "admin" && targetRole === "owner") return false;
  return true;
}

export function canInviteRole(actingRole: Role, roleToGrant: Role): boolean {
  if (!canManageMembers(actingRole)) return false;
  if (actingRole === "admin" && roleToGrant === "owner") return false;
  return true;
}

export function canViewAuditLog(role: Role): boolean {
  return role === "owner" || role === "admin";
}

export function canTransferOwnership(role: Role): boolean {
  return role === "owner";
}

export function canDeactivateOrganization(role: Role): boolean {
  return role === "owner";
}

/** Mirrors `Permission.MANAGE_DATA_SOURCES`: create, edit, test, replace
 * credentials, enable, disable. */
export function canManageDataSources(role: Role): boolean {
  return role === "owner" || role === "admin";
}

/** Mirrors `Permission.DELETE_DATA_SOURCES`, deliberately owner-only -- see
 * `app.tenancy.permissions` for why deletion sits apart from the general
 * data-source management permission. */
export function canDeleteDataSources(role: Role): boolean {
  return role === "owner";
}

export const ASSIGNABLE_ROLES: Role[] = ["viewer", "analyst", "admin", "owner"];

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  analyst: "Analyst",
  viewer: "Viewer",
};
