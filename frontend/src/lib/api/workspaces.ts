import { request } from "@/lib/api/client";
import type {
  AcceptInvitationRequest,
  AuditLogList,
  ChangeRoleRequest,
  InviteMemberRequest,
  Membership,
  MembershipList,
  Invitation,
  ReportPreferences,
  ReportPreferencesUpdateRequest,
  TransferOwnershipRequest,
  UserSettings,
  Workspace,
  WorkspaceCreateRequest,
  WorkspaceList,
  WorkspaceUpdateRequest,
} from "@/types/api";
import { baseUrl, readCsrfCookie } from "@/lib/api/client";

export const workspacesApi = {
  list: () => request<WorkspaceList>("/api/v1/workspaces"),
  create: (body: WorkspaceCreateRequest) =>
    request<Workspace>("/api/v1/workspaces", { method: "POST", body: JSON.stringify(body) }),
  get: (workspaceId: string) => request<Workspace>(`/api/v1/workspaces/${workspaceId}`),
  update: (workspaceId: string, body: WorkspaceUpdateRequest) =>
    request<Workspace>(`/api/v1/workspaces/${workspaceId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deactivate: (workspaceId: string) =>
    request<Workspace>(`/api/v1/workspaces/${workspaceId}/deactivate`, { method: "POST" }),
  leave: (workspaceId: string) =>
    request<{ message: string }>(`/api/v1/workspaces/${workspaceId}/leave`, { method: "POST" }),
  transferOwnership: (workspaceId: string, body: TransferOwnershipRequest) =>
    request<Membership>(`/api/v1/workspaces/${workspaceId}/transfer-ownership`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  acceptInvitation: (body: AcceptInvitationRequest) =>
    request<Membership>("/api/v1/invitations/accept", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listAuditLog: (workspaceId: string, limit = 50, offset = 0) =>
    request<AuditLogList>(
      `/api/v1/workspaces/${workspaceId}/audit-log?limit=${limit}&offset=${offset}`,
    ),

  getReportPreferences: (workspaceId: string) =>
    request<ReportPreferences>(`/api/v1/workspaces/${workspaceId}/report-preferences`),
  updateReportPreferences: (workspaceId: string, body: ReportPreferencesUpdateRequest) =>
    request<ReportPreferences>(`/api/v1/workspaces/${workspaceId}/report-preferences`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  /**
   * Multipart upload -- deliberately bypasses the shared `request()` helper,
   * which always sets `Content-Type: application/json`. Still needs the same
   * cookie/CSRF treatment `request()` gives every other mutating call.
   */
  setProfileImage: async (workspaceId: string, file: File): Promise<UserSettings> => {
    const body = new FormData();
    body.append("file", file);
    const csrf = readCsrfCookie();
    const response = await fetch(`${baseUrl()}/api/v1/workspaces/${workspaceId}/profile-image`, {
      method: "POST",
      credentials: "include",
      headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
      body,
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = payload?.detail;
      const message = typeof detail === "string" ? detail : detail?.message;
      throw new Error(message ?? "The profile image could not be uploaded.");
    }
    return payload as UserSettings;
  },
};

export const membershipsApi = {
  list: (workspaceId: string) =>
    request<MembershipList>(`/api/v1/workspaces/${workspaceId}/members`),
  invite: (workspaceId: string, body: InviteMemberRequest) =>
    request<Invitation>(`/api/v1/workspaces/${workspaceId}/members/invite`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  changeRole: (workspaceId: string, userId: string, body: ChangeRoleRequest) =>
    request<Membership>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (workspaceId: string, userId: string) =>
    request<Membership>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
      method: "DELETE",
    }),
};
