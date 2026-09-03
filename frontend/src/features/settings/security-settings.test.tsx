import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SecuritySettings } from "./security-settings";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import type { UserSettings } from "@/types/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/auth", () => ({
  authApi: { changePassword: vi.fn(), logoutAll: vi.fn(), resendVerification: vi.fn() },
}));
vi.mock("@/lib/api/users", () => ({ usersApi: { getSettings: vi.fn() } }));

function settings(overrides: Partial<UserSettings> = {}): UserSettings {
  return {
    id: "u1",
    email: "ada@example.com",
    pending_email: null,
    display_name: "Ada",
    preferred_timezone: "UTC",
    preferred_locale: "en-US",
    profile_image_artifact_id: null,
    profile_image_workspace_id: null,
    is_active: true,
    email_verified: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    last_login_at: null,
    ...overrides,
  };
}

describe("SecuritySettings", () => {
  beforeEach(() => vi.resetAllMocks());

  it("changes the password after client-side validation passes", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    vi.mocked(authApi.changePassword).mockResolvedValue({
      message: "Password changed. Other sessions have been signed out.",
    });
    render(<SecuritySettings />);

    fireEvent.change(await screen.findByLabelText("Current password"), {
      target: { value: "old-password-1" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-1" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-password-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    await waitFor(() =>
      expect(authApi.changePassword).toHaveBeenCalledWith({
        current_password: "old-password-1",
        new_password: "new-password-1",
      }),
    );
    expect(await screen.findByText(/Other sessions have been signed out/)).toBeInTheDocument();
  });

  it("rejects a mismatched confirmation before calling the API", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    render(<SecuritySettings />);

    fireEvent.change(await screen.findByLabelText("Current password"), {
      target: { value: "old-password-1" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-1" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "different-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(authApi.changePassword).not.toHaveBeenCalled();
  });

  it("requires confirmation before signing out of every device, then redirects to login", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    vi.mocked(authApi.logoutAll).mockResolvedValue({ message: "Signed out." });
    render(<SecuritySettings />);

    fireEvent.click(await screen.findByRole("button", { name: "Sign out of all devices" }));
    expect(authApi.logoutAll).not.toHaveBeenCalled();

    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Sign out everywhere" }));

    await waitFor(() => expect(authApi.logoutAll).toHaveBeenCalled());
    expect(push).toHaveBeenCalledWith("/login");
  });

  it("does not offer viewing or revoking individual sessions, and says so", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    render(<SecuritySettings />);

    await screen.findByText(/isn.t available yet/);
    expect(screen.queryByRole("button", { name: /revoke/i })).not.toBeInTheDocument();
  });

  it("offers to resend verification only when the email is unverified", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings({ email_verified: false }));
    vi.mocked(authApi.resendVerification).mockResolvedValue({ message: "Sent." });
    render(<SecuritySettings />);

    const resend = await screen.findByRole("button", { name: "Resend verification email" });
    fireEvent.click(resend);

    await waitFor(() => expect(authApi.resendVerification).toHaveBeenCalled());
  });

  it("hides the resend control once the email is verified", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings({ email_verified: true }));
    render(<SecuritySettings />);

    await screen.findByText("Verified");
    expect(screen.queryByRole("button", { name: /Resend verification/ })).not.toBeInTheDocument();
  });

  it("shows an error instead of a broken page when settings fail to load", async () => {
    vi.mocked(usersApi.getSettings).mockRejectedValue(
      new ApiError("Security settings unavailable.", 500),
    );
    render(<SecuritySettings />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Security settings unavailable.");
  });
});
