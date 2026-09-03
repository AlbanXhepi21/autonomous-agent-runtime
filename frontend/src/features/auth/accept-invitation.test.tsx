import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AcceptInvitation } from "./accept-invitation";
import { workspacesApi } from "@/lib/api/workspaces";
import { ApiError } from "@/lib/api/client";
import { readLastWorkspaceId } from "@/lib/auth/last-workspace";

const push = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => searchParams,
}));
vi.mock("@/lib/api/workspaces", () => ({ workspacesApi: { acceptInvitation: vi.fn() } }));

describe("AcceptInvitation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    searchParams = new URLSearchParams({ token: "invite-token" });
  });

  it("accepts the invitation and opens the joined workspace", async () => {
    vi.mocked(workspacesApi.acceptInvitation).mockResolvedValue({
      id: "m1",
      user_id: "u1",
      workspace_id: "ws-9",
      role: "analyst",
      status: "active",
      invited_by: null,
      joined_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    render(<AcceptInvitation />);

    await waitFor(() => expect(push).toHaveBeenCalledWith("/w/ws-9"));
    expect(workspacesApi.acceptInvitation).toHaveBeenCalledWith({ token: "invite-token" });
    expect(readLastWorkspaceId()).toBe("ws-9");
  });

  it("sends an unauthenticated caller to login with the invitation link preserved as the return path", async () => {
    vi.mocked(workspacesApi.acceptInvitation).mockRejectedValue(
      new ApiError("Sign in required.", 401),
    );

    render(<AcceptInvitation />);

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        `/login?next=${encodeURIComponent("/invitations/accept?token=invite-token")}`,
      ),
    );
  });

  it("shows an already-a-member error instead of redirecting", async () => {
    vi.mocked(workspacesApi.acceptInvitation).mockRejectedValue(
      new ApiError("You are already a member of this workspace.", 409, "already_a_member"),
    );

    render(<AcceptInvitation />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You are already a member of this workspace.",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("explains a missing token without calling the API", () => {
    searchParams = new URLSearchParams();
    render(<AcceptInvitation />);

    expect(screen.getByRole("alert")).toHaveTextContent("missing its token");
    expect(workspacesApi.acceptInvitation).not.toHaveBeenCalled();
  });
});
