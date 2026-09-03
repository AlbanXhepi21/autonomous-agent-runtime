import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsProvider, useSettings } from "./settings-context";
import { ApiError } from "@/lib/api/client";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { Workspace } from "@/types/api";

vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn(), update: vi.fn() },
  membershipsApi: { list: vi.fn() },
}));

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

function Probe() {
  const { loading, error, workspace: ws, role } = useSettings();
  if (loading) return <div>loading</div>;
  if (error) return <div role="alert">{error}</div>;
  return (
    <div>
      <div data-testid="name">{ws?.name}</div>
      <div data-testid="role">{role}</div>
    </div>
  );
}

describe("SettingsProvider", () => {
  beforeEach(() => vi.resetAllMocks());

  it("shows a loading state before settings resolve", async () => {
    let resolveWorkspace: (value: Workspace) => void = () => {};
    vi.mocked(workspacesApi.get).mockImplementation(
      () => new Promise((resolve) => (resolveWorkspace = resolve)),
    );
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [] });

    render(
      <SettingsProvider
        workspaceId="ws-1"
        currentUserId="u1"
        currentUserDisplayName="Ada"
        currentUserEmail="a@example.com"
      >
        <Probe />
      </SettingsProvider>,
    );

    expect(screen.getByText("loading")).toBeInTheDocument();
    resolveWorkspace(workspace());
    await waitFor(() => expect(screen.getByTestId("name")).toHaveTextContent("Acme"));
  });

  it("surfaces a load error instead of rendering stale content", async () => {
    vi.mocked(workspacesApi.get).mockRejectedValue(new ApiError("Workspace not found.", 404));
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [] });

    render(
      <SettingsProvider
        workspaceId="ws-1"
        currentUserId="u1"
        currentUserDisplayName="Ada"
        currentUserEmail="a@example.com"
      >
        <Probe />
      </SettingsProvider>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Workspace not found.");
  });

  it("derives the caller's own role from the membership list", async () => {
    vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
    vi.mocked(membershipsApi.list).mockResolvedValue({
      items: [
        {
          id: "m1",
          user_id: "u1",
          workspace_id: "ws-1",
          role: "admin",
          status: "active",
          invited_by: null,
          joined_at: "2026-01-01T00:00:00Z",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
    });

    render(
      <SettingsProvider
        workspaceId="ws-1"
        currentUserId="u1"
        currentUserDisplayName="Ada"
        currentUserEmail="a@example.com"
      >
        <Probe />
      </SettingsProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("role")).toHaveTextContent("admin"));
  });

  it("re-fetches fresh data instead of keeping the previous tenant's when the workspace id changes", async () => {
    vi.mocked(workspacesApi.get).mockImplementation((id) =>
      Promise.resolve(workspace({ id, name: id === "ws-1" ? "Acme" : "Globex" })),
    );
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [] });

    const { rerender } = render(
      <SettingsProvider
        workspaceId="ws-1"
        currentUserId="u1"
        currentUserDisplayName="Ada"
        currentUserEmail="a@example.com"
      >
        <Probe />
      </SettingsProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("name")).toHaveTextContent("Acme"));

    rerender(
      <SettingsProvider
        workspaceId="ws-2"
        currentUserId="u1"
        currentUserDisplayName="Ada"
        currentUserEmail="a@example.com"
      >
        <Probe />
      </SettingsProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("name")).toHaveTextContent("Globex"));
    expect(screen.queryByText("Acme")).not.toBeInTheDocument();
  });
});
