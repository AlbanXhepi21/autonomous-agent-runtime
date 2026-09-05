import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileSettings } from "./profile-settings";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import { workspacesApi } from "@/lib/api/workspaces";
import type { UserSettings } from "@/types/api";

vi.mock("@/lib/api/users", () => ({
  usersApi: { getSettings: vi.fn(), updateSettings: vi.fn(), requestEmailChange: vi.fn() },
}));
vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { setProfileImage: vi.fn() },
}));

function settings(overrides: Partial<UserSettings> = {}): UserSettings {
  return {
    id: "u1",
    email: "ada@example.com",
    pending_email: null,
    display_name: "Ada Lovelace",
    preferred_timezone: "UTC",
    preferred_locale: "en-US",
    profile_image_artifact_id: null,
    profile_image_workspace_id: null,
    is_active: true,
    email_verified: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    last_login_at: null,
    ...overrides,
  };
}

/**
 * `ProfileSettings` is workspace-independent -- it no longer needs
 * `SettingsProvider` at all. `uploadWorkspaceId` is the one exception: the
 * profile-image upload still goes through a workspace-scoped artifact route
 * (see `profile-settings.tsx`), so the page-level caller resolves it and
 * passes it down as a plain prop.
 */
function renderProfile(uploadWorkspaceId: string | null = "ws-1") {
  return render(<ProfileSettings uploadWorkspaceId={uploadWorkspaceId} />);
}

describe("ProfileSettings", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows a loading state before the profile resolves", () => {
    vi.mocked(usersApi.getSettings).mockImplementation(() => new Promise(() => {}));
    renderProfile();

    expect(screen.getByText("Loading profile…")).toBeInTheDocument();
  });

  it("shows an error instead of a broken form when the profile fails to load", async () => {
    vi.mocked(usersApi.getSettings).mockRejectedValue(new ApiError("Profile unavailable.", 500));
    renderProfile();

    expect(await screen.findByRole("alert")).toHaveTextContent("Profile unavailable.");
  });

  it("saves a display name change", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    vi.mocked(usersApi.updateSettings).mockResolvedValue(
      settings({ display_name: "Ada K. Lovelace" }),
    );
    renderProfile();

    const nameInput = await screen.findByLabelText("Display name");
    fireEvent.change(nameInput, { target: { value: "Ada K. Lovelace" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(usersApi.updateSettings).toHaveBeenCalledWith({
        display_name: "Ada K. Lovelace",
        preferred_timezone: "UTC",
        preferred_locale: "en-US",
      }),
    );
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("starts the email-change flow and requires the current password", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    renderProfile();

    fireEvent.click(await screen.findByRole("button", { name: "Change email" }));
    fireEvent.change(screen.getByLabelText("New email"), {
      target: { value: "ada-new@example.com" },
    });
    // fireEvent.click on the submit button runs jsdom's native required-field
    // validation first, which would block the form before this component's
    // own (better-worded) validation ever runs. Submitting the form directly
    // exercises that custom validation instead.
    fireEvent.submit(screen.getByRole("button", { name: "Send confirmation" }).closest("form")!);

    expect(await screen.findByText("Enter your current password.")).toBeInTheDocument();
    expect(usersApi.requestEmailChange).not.toHaveBeenCalled();
  });

  it("does not refetch when the caller's active organization changes", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    const { rerender } = render(<ProfileSettings uploadWorkspaceId="ws-1" />);
    await screen.findByLabelText("Display name");

    // Simulates switching organizations: only the upload target prop
    // changes, exactly as the personal-settings page passes down a freshly
    // resolved workspace after a tenant switch. Profile data itself must not
    // be re-requested -- it was never scoped to a workspace in the first
    // place.
    rerender(<ProfileSettings uploadWorkspaceId="ws-2" />);

    expect(usersApi.getSettings).toHaveBeenCalledTimes(1);
  });

  it("disables the image upload when the caller has no workspace to upload into", async () => {
    vi.mocked(usersApi.getSettings).mockResolvedValue(settings());
    renderProfile(null);

    const button = await screen.findByRole("button", { name: "Change image" });
    expect(button).toBeDisabled();
    expect(await screen.findByText("Join or create an organization to add a profile image.")).toBeInTheDocument();
    expect(workspacesApi.setProfileImage).not.toHaveBeenCalled();
  });
});
