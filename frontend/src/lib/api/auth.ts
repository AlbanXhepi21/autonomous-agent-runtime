import { request } from "@/lib/api/client";
import type {
  AuthMessage,
  AuthUser,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  RegisterRequest,
  ResetPasswordRequest,
  VerifyEmailConfirmRequest,
} from "@/types/api";

export const authApi = {
  register: (body: RegisterRequest) =>
    request<AuthUser>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: LoginRequest) =>
    request<AuthUser>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request<AuthMessage>("/api/v1/auth/logout", { method: "POST" }),
  logoutAll: () => request<AuthMessage>("/api/v1/auth/logout-all", { method: "POST" }),
  me: () => request<AuthUser>("/api/v1/auth/me"),
  forgotPassword: (body: ForgotPasswordRequest) =>
    request<AuthMessage>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  resetPassword: (body: ResetPasswordRequest) =>
    request<AuthMessage>("/api/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  changePassword: (body: ChangePasswordRequest) =>
    request<AuthMessage>("/api/v1/auth/change-password", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  resendVerification: () =>
    request<AuthMessage>("/api/v1/auth/verify-email/resend", { method: "POST" }),
  confirmEmailVerification: (body: VerifyEmailConfirmRequest) =>
    request<AuthMessage>("/api/v1/auth/verify-email/confirm", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
