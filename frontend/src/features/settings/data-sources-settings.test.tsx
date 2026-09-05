import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  DataSourcesSettings,
  describeStatus,
  maskHost,
  readOnlyLabel,
} from "./data-sources-settings";
import { SettingsProvider } from "./settings-context";
import { SettingsLoadedGate } from "./test-support";
import { ApiError } from "@/lib/api/client";
import { dataSourcesApi } from "@/lib/api/datasources";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import type { DataSource, Membership, Role, Workspace } from "@/types/api";

vi.mock("@/lib/api/workspaces", () => ({
  workspacesApi: { get: vi.fn() },
  membershipsApi: { list: vi.fn() },
}));

vi.mock("@/lib/api/datasources", () => ({
  dataSourcesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    replaceCredentials: vi.fn(),
    testConnection: vi.fn(),
    verifyReadOnly: vi.fn(),
    enable: vi.fn(),
    disable: vi.fn(),
    remove: vi.fn(),
  },
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

function member(role: Role, overrides: Partial<Membership> = {}): Membership {
  return {
    id: "m1",
    user_id: "u1",
    workspace_id: "ws-1",
    role,
    status: "active",
    invited_by: null,
    joined_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function dataSource(overrides: Partial<DataSource> = {}): DataSource {
  return {
    id: "ds-1",
    workspace_id: "ws-1",
    name: "Primary Analytics",
    description: "Read replica used for reporting",
    engine: "postgresql",
    environment: "production",
    host: "db.internal.acme.com",
    port: 5432,
    database: "analytics",
    username: "ro_user",
    ssl_mode: "require",
    allowed_schemas: ["public"],
    statement_timeout_seconds: 15,
    connection_timeout_seconds: 10,
    source_timezone: null,
    max_result_rows: 5000,
    max_result_bytes: 1000000,
    status: "active",
    health_status: "healthy",
    last_connection_at: "2026-01-02T10:00:00Z",
    last_connection_error: null,
    last_error_category: null,
    last_successful_connection_at: "2026-01-02T10:00:00Z",
    last_profiled_at: null,
    created_by: "u1",
    version: 1,
    deleted_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T10:00:00Z",
    ...overrides,
  };
}

function renderWith(role: Role, items: DataSource[], workspaceId = "ws-1") {
  vi.mocked(workspacesApi.get).mockResolvedValue(workspace({ id: workspaceId }));
  vi.mocked(membershipsApi.list).mockResolvedValue({
    items: [member(role, { workspace_id: workspaceId })],
  });
  vi.mocked(dataSourcesApi.list).mockResolvedValue({
    items, total: items.length, limit: 30, offset: 0,
  });
  return render(
    <SettingsProvider
      workspaceId={workspaceId}
      currentUserId="u1"
      currentUserDisplayName="Ada"
      currentUserEmail="a@example.com"
    >
      <SettingsLoadedGate>
        <DataSourcesSettings />
      </SettingsLoadedGate>
    </SettingsProvider>,
  );
}

describe("badge and formatting helpers", () => {
  it("maps every backend status to a documented badge", () => {
    expect(describeStatus("active", null).label).toBe("Connected");
    expect(describeStatus("pending", null).label).toBe("Draft");
    expect(describeStatus("testing", null).label).toBe("Requires review");
    expect(describeStatus("verified_read_only", null).label).toBe("Requires review");
    expect(describeStatus("disabled", null).label).toBe("Disabled");
    expect(describeStatus("failed", "authentication_failed").label).toBe("Authentication failed");
    expect(describeStatus("failed", "network_unreachable").label).toBe("Unreachable");
    expect(describeStatus("failed", null).label).toBe("Unreachable");
  });

  it("derives read-only status from onboarding progress, not a live check", () => {
    expect(readOnlyLabel("active")).toBe("Read-only verified");
    expect(readOnlyLabel("verified_read_only")).toBe("Read-only verified");
    expect(readOnlyLabel("pending")).toBe("Not yet verified");
    expect(readOnlyLabel("disabled")).toBe("Unknown");
  });

  it("masks a host without revealing most of it", () => {
    const masked = maskHost("db.internal.acme.com");
    expect(masked).not.toBe("db.internal.acme.com");
    expect(masked.startsWith("db")).toBe(true);
    expect(masked.endsWith(".com")).toBe(true);
    expect(masked).toContain("•");
  });
});

describe("DataSourcesSettings", () => {
  beforeEach(() => vi.resetAllMocks());

  it("shows the empty state when there are no connections", async () => {
    renderWith("owner", []);

    expect(await screen.findByText("No data sources connected")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Add a read-only PostgreSQL database to begin analyzing your organization's data.",
      ),
    ).toBeInTheDocument();
  });

  it("shows a loading skeleton before the first fetch resolves", async () => {
    let resolveList: (value: { items: DataSource[]; total: number; limit: number; offset: number }) => void =
      () => {};
    vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [member("owner")] });
    vi.mocked(dataSourcesApi.list).mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      }),
    );

    render(
      <SettingsProvider workspaceId="ws-1" currentUserId="u1" currentUserDisplayName="Ada" currentUserEmail="a@example.com">
        <SettingsLoadedGate>
          <DataSourcesSettings />
        </SettingsLoadedGate>
      </SettingsProvider>,
    );

    expect(await screen.findByLabelText("Loading data sources")).toBeInTheDocument();
    resolveList({ items: [], total: 0, limit: 30, offset: 0 });
    await waitFor(() => expect(screen.getByText("No data sources connected")).toBeInTheDocument());
  });

  it("shows a safe error message, never a raw exception, when loading fails", async () => {
    vi.mocked(workspacesApi.get).mockResolvedValue(workspace());
    vi.mocked(membershipsApi.list).mockResolvedValue({ items: [member("owner")] });
    vi.mocked(dataSourcesApi.list).mockRejectedValue(
      new ApiError("Data sources could not be loaded.", 500),
    );

    render(
      <SettingsProvider workspaceId="ws-1" currentUserId="u1" currentUserDisplayName="Ada" currentUserEmail="a@example.com">
        <SettingsLoadedGate>
          <DataSourcesSettings />
        </SettingsLoadedGate>
      </SettingsProvider>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Data sources could not be loaded.");
  });

  it("lists connections with environment, status, and read-only badges", async () => {
    renderWith("owner", [
      dataSource({ name: "Primary", environment: "production", status: "active" }),
      dataSource({ id: "ds-2", name: "Staging copy", environment: "staging", status: "pending" }),
    ]);

    expect(await screen.findByText("Primary")).toBeInTheDocument();
    expect(screen.getByText("Production")).toBeInTheDocument();
    expect(screen.getByText("· Read only")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByText("Staging copy")).toBeInTheDocument();
    expect(screen.getByText("Staging")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("never displays the host in full by default", async () => {
    renderWith("owner", [dataSource({ host: "db.internal.acme.com" })]);

    await screen.findByText("Primary Analytics");
    expect(screen.queryByText("db.internal.acme.com")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show host" }));
    expect(screen.getByText("db.internal.acme.com")).toBeInTheDocument();
  });

  it("hides management actions and the add button from an analyst", async () => {
    renderWith("analyst", [dataSource()]);

    await screen.findByText("Primary Analytics");
    expect(screen.queryByRole("button", { name: "Add connection" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Actions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("hides management actions from a viewer, showing only safe status", async () => {
    renderWith("viewer", [dataSource()]);

    await screen.findByText("Primary Analytics");
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add connection" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("shows delete only to an owner, not an admin", async () => {
    renderWith("admin", [dataSource()]);

    await screen.findByText("Primary Analytics");
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("validates required fields before creating a connection", async () => {
    renderWith("owner", []);
    await screen.findByText("No data sources connected");

    fireEvent.click(screen.getByRole("button", { name: "Add connection" }));
    fireEvent.click(await screen.findByRole("button", { name: "Save as draft" }));

    expect(await screen.findByText("Name is required.")).toBeInTheDocument();
    expect(screen.getByText("Host is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(dataSourcesApi.create).not.toHaveBeenCalled();
  });

  it("creates a draft with the submitted fields and backend-matching defaults", async () => {
    const created = dataSource({ id: "ds-new", status: "pending" });
    vi.mocked(dataSourcesApi.create).mockResolvedValue(created);
    renderWith("owner", []);
    await screen.findByText("No data sources connected");

    fireEvent.click(screen.getByRole("button", { name: "Add connection" }));
    fireEvent.change(await screen.findByLabelText("Name"), { target: { value: "Primary Analytics" } });
    fireEvent.change(screen.getByLabelText("Host"), { target: { value: "db.example.com" } });
    fireEvent.change(screen.getByLabelText("Database"), { target: { value: "analytics" } });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "ro_user" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "super-secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Save as draft" }));

    await waitFor(() =>
      expect(dataSourcesApi.create).toHaveBeenCalledWith(
        "ws-1",
        expect.objectContaining({
          name: "Primary Analytics",
          host: "db.example.com",
          database: "analytics",
          username: "ro_user",
          password: "super-secret",
          engine: "postgresql",
          environment: "development",
          ssl_mode: "require",
          port: 5432,
          statement_timeout_seconds: 15,
          connection_timeout_seconds: 10,
          max_result_rows: 5000,
          max_result_bytes: 1000000,
          allowed_schemas: ["public"],
        }),
      ),
    );
    expect(await screen.findByText(/was saved as a draft/)).toBeInTheDocument();
    expect(dataSourcesApi.testConnection).not.toHaveBeenCalled();
  });

  it("save and enable creates the draft then immediately tests it", async () => {
    const created = dataSource({ id: "ds-new", status: "pending" });
    vi.mocked(dataSourcesApi.create).mockResolvedValue(created);
    vi.mocked(dataSourcesApi.testConnection).mockResolvedValue({
      success: true,
      message: "Connected successfully.",
      error_category: null,
      server_version: "PostgreSQL 17.0",
      ssl_active: true,
      accessible_schemas: ["public"],
      latency_ms: 12.3,
      tested_at: "2026-01-03T00:00:00Z",
    });
    renderWith("owner", []);
    await screen.findByText("No data sources connected");

    fireEvent.click(screen.getByRole("button", { name: "Add connection" }));
    fireEvent.change(await screen.findByLabelText("Name"), { target: { value: "Primary" } });
    fireEvent.change(screen.getByLabelText("Host"), { target: { value: "db.example.com" } });
    fireEvent.change(screen.getByLabelText("Database"), { target: { value: "analytics" } });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "ro_user" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "super-secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Save and enable" }));

    await waitFor(() => expect(dataSourcesApi.create).toHaveBeenCalled());
    await waitFor(() => expect(dataSourcesApi.testConnection).toHaveBeenCalledWith("ws-1", "ds-new"));
    expect(await screen.findByText("Connection succeeded")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL 17.0")).toBeInTheDocument();
    // The backend's own already-safe fields are shown; nothing resembling a
    // raw driver exception, password, or connection string is rendered.
    expect(screen.queryByText(/super-secret/)).not.toBeInTheDocument();
  });

  it("shows a safe message, not a raw exception, when a test fails", async () => {
    vi.mocked(dataSourcesApi.testConnection).mockRejectedValue(
      new ApiError("Analytics database is unavailable.", 422, "connection_refused"),
    );
    renderWith("owner", [dataSource({ status: "pending" })]);
    await screen.findByText("Primary Analytics");

    fireEvent.click(screen.getByRole("button", { name: "Test connection" }));

    expect(await screen.findByText("Analytics database is unavailable.")).toBeInTheDocument();
  });

  it("never prefills or displays the password when editing, and offers replace-credentials separately", async () => {
    renderWith("owner", [dataSource()]);
    await screen.findByText("Primary Analytics");

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    const dialog = await screen.findByRole("dialog", { name: "Edit Primary Analytics" });
    const passwordField = within(dialog).getByLabelText("Password");
    expect(passwordField).toHaveValue("Password configured");
    expect(passwordField).toBeDisabled();
    expect(passwordField).not.toHaveAttribute("type", "password");
  });

  it("warns before applying a connection-critical change", async () => {
    renderWith("owner", [dataSource()]);
    await screen.findByText("Primary Analytics");
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit Primary Analytics" });

    fireEvent.change(within(dialog).getByLabelText("Host"), { target: { value: "new-host.example.com" } });

    expect(await screen.findByText(/resets this connection to Draft/)).toBeInTheDocument();
  });

  it("replaces credentials via a dedicated dialog requiring a matching confirmation", async () => {
    const updated = dataSource({ status: "pending", version: 2 });
    vi.mocked(dataSourcesApi.replaceCredentials).mockResolvedValue(updated);
    renderWith("owner", [dataSource()]);
    await screen.findByText("Primary Analytics");

    fireEvent.click(screen.getByRole("button", { name: "Replace credentials" }));
    const dialog = await screen.findByRole("dialog", { name: "Replace credentials: Primary Analytics" });
    fireEvent.change(within(dialog).getByLabelText("New password"), { target: { value: "rotated-secret" } });
    fireEvent.change(within(dialog).getByLabelText("Confirm new password"), {
      target: { value: "different" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Replace credentials" }));
    expect(await screen.findByText("The passwords don't match.")).toBeInTheDocument();
    expect(dataSourcesApi.replaceCredentials).not.toHaveBeenCalled();

    fireEvent.change(within(dialog).getByLabelText("Confirm new password"), {
      target: { value: "rotated-secret" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Replace credentials" }));

    await waitFor(() =>
      expect(dataSourcesApi.replaceCredentials).toHaveBeenCalledWith("ws-1", "ds-1", {
        password: "rotated-secret",
      }),
    );
  });

  it("requires confirmation before disabling, and explains the effect", async () => {
    vi.mocked(dataSourcesApi.disable).mockResolvedValue(dataSource({ status: "disabled" }));
    renderWith("owner", [dataSource()]);
    await screen.findByText("Primary Analytics");

    fireEvent.click(screen.getByRole("button", { name: "Disable" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByText(/New analysis runs will no longer/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Historical runs and reports/)).toBeInTheDocument();
    expect(dataSourcesApi.disable).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByRole("button", { name: "Disable" }));
    await waitFor(() => expect(dataSourcesApi.disable).toHaveBeenCalledWith("ws-1", "ds-1"));
  });

  it("requires typing the exact name before deleting", async () => {
    vi.mocked(dataSourcesApi.remove).mockResolvedValue(dataSource({ status: "deleted" }));
    renderWith("owner", [dataSource()]);
    await screen.findByText("Primary Analytics");

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("alertdialog");
    const confirmButton = within(dialog).getByRole("button", { name: "Delete data source" });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/Type/), { target: { value: "wrong name" } });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/Type/), { target: { value: "Primary Analytics" } });
    expect(confirmButton).not.toBeDisabled();
    fireEvent.click(confirmButton);

    await waitFor(() => expect(dataSourcesApi.remove).toHaveBeenCalledWith("ws-1", "ds-1"));
  });

  it("surfaces a 403 from the backend as a readable message instead of crashing", async () => {
    vi.mocked(dataSourcesApi.remove).mockRejectedValue(
      new ApiError("Missing permission: delete_data_sources", 403, "permission_denied"),
    );
    renderWith("owner", [dataSource()]);
    await screen.findByText("Primary Analytics");

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.change(within(dialog).getByLabelText(/Type/), { target: { value: "Primary Analytics" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete data source" }));

    // A 403 gets a clear, friendly message rather than the backend's raw
    // permission-code text -- and the dialog stays usable, it doesn't crash.
    expect(await screen.findByText("Only an owner can delete a data source.")).toBeInTheDocument();
  });

  it("never shows stale data from a previous organization after switching", async () => {
    vi.mocked(workspacesApi.get).mockImplementation((id: string) =>
      Promise.resolve(workspace({ id })),
    );
    vi.mocked(membershipsApi.list).mockImplementation((id: string) =>
      Promise.resolve({ items: [member("owner", { workspace_id: id })] }),
    );
    let resolveWorkspaceOneList: (value: { items: DataSource[]; total: number; limit: number; offset: number }) => void =
      () => {};
    vi.mocked(dataSourcesApi.list).mockImplementation((id: string) => {
      if (id === "ws-1") {
        return new Promise((resolve) => {
          resolveWorkspaceOneList = resolve;
        });
      }
      return Promise.resolve({
        items: [dataSource({ id: "ds-2", workspace_id: "ws-2", name: "Org Two Source" })],
        total: 1,
        limit: 30,
        offset: 0,
      });
    });

    const { rerender } = render(
      <SettingsProvider workspaceId="ws-1" currentUserId="u1" currentUserDisplayName="Ada" currentUserEmail="a@example.com">
        <SettingsLoadedGate>
          <DataSourcesSettings />
        </SettingsLoadedGate>
      </SettingsProvider>,
    );
    await screen.findByLabelText("Loading data sources");

    // Switch organizations before ws-1's request ever resolves.
    rerender(
      <SettingsProvider workspaceId="ws-2" currentUserId="u1" currentUserDisplayName="Ada" currentUserEmail="a@example.com">
        <SettingsLoadedGate>
          <DataSourcesSettings />
        </SettingsLoadedGate>
      </SettingsProvider>,
    );

    expect(await screen.findByText("Org Two Source")).toBeInTheDocument();

    // The old organization's request finally resolves -- it must not
    // resurrect ws-1's (empty, in this test) list or clobber ws-2's.
    resolveWorkspaceOneList({ items: [], total: 0, limit: 30, offset: 0 });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.getByText("Org Two Source")).toBeInTheDocument();
    expect(screen.queryByText("No data sources connected")).not.toBeInTheDocument();
  });
});
