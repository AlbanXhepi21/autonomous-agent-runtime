import { request } from "@/lib/api/client";
import type {
  AuthMessage,
  ConfirmEmailChangeRequest,
  RequestEmailChangeRequest,
  UserSettings,
  UserSettingsUpdateRequest,
} from "@/types/api";

export const usersApi = {
  getSettings: () => request<UserSettings>("/api/v1/users/me"),
  updateSettings: (body: UserSettingsUpdateRequest) =>
    request<UserSettings>("/api/v1/users/me", { method: "PATCH", body: JSON.stringify(body) }),
  requestEmailChange: (body: RequestEmailChangeRequest) =>
    request<AuthMessage>("/api/v1/users/me/email-change/request", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  confirmEmailChange: (body: ConfirmEmailChangeRequest) =>
    request<UserSettings>("/api/v1/users/me/email-change/confirm", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
