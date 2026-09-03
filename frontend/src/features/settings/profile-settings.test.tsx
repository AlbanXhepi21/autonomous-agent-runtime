import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileSettings } from "./profile-settings";
import { SettingsProvider } from "./settings-context";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { UserSettings, Workspace } from "@/types/api";

vi.mock("@/lib/api/users", () => ({
  usersApi: { getSettings: vi.fn(), updateSettings: vi.fn(), requestEmailChange: vi.fn() },
}));
vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn(), setProfileImage: vi.fn() },
  membershipsApi: { list: vi.fn() },
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

function workspace(): Workspace {
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
  };
}

function renderProfile() {
  return render(
    <SettingsProvider
      workspaceId="ws-1"
      currentUserId="u1"
      currentUserDisplayName="Ada"
      currentUserEmail="ada@example.com"
    >
      <ProfileSettings />
    </SettingsProvider>,
  );
}

describe("ProfileSettings", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [] });
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
});
