import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Workbench } from "./workbench";
import { analyticsApi } from "@/lib/api/analytics";
import { conversationsApi } from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/client";
import { approvalsApi } from "@/lib/api/approvals";
import { configApi } from "@/lib/api/config";
import type { PublicRunEvent } from "@/types/analytics";

vi.mock("@/lib/api/analytics", () => ({
  analyticsApi: { createRun: vi.fn(), getRun: vi.fn(), connect: vi.fn() },
}));
vi.mock("@/lib/api/conversations", () => ({
  conversationsApi: {
    create: vi.fn(),
    list: vi.fn(),
    get: vi.fn(),
    rename: vi.fn(),
    remove: vi.fn(),
  },
}));
vi.mock("@/lib/api/approvals", () => ({
  approvalsApi: { list: vi.fn(), approve: vi.fn(), reject: vi.fn() },
}));
vi.mock("@/lib/api/config", () => ({ configApi: { get: vi.fn() } }));

describe("Workbench", () => {
  const connect = vi.mocked(analyticsApi.connect);
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(conversationsApi.list).mockResolvedValue({
      items: [],
      total: 0,
      limit: 30,
      offset: 0,
    });
    vi.mocked(approvalsApi.list).mockResolvedValue([]);
    vi.mocked(configApi.get).mockResolvedValue({ developer_mode: false });
  });

  it("offers the memory inspector only when the server reports developer mode", async () => {
    render(<Workbench />);
    await waitFor(() => expect(configApi.get).toHaveBeenCalled());
    expect(screen.queryByText(/memory/i)).not.toBeInTheDocument();

    vi.mocked(configApi.get).mockResolvedValue({ developer_mode: true });
    render(<Workbench />);
    await waitFor(() => expect(screen.getAllByText(/memory/i).length).toBeGreaterThan(0));
  });

  it("submits a message and shows running status", async () => {
    vi.mocked(analyticsApi.createRun).mockResolvedValue({
      run_id: "run-1",
      conversation_id: "c-1",
      status: "running",
    });
    connect.mockReturnValue({ close: vi.fn() } as unknown as EventSource);
    render(<Workbench />);
    fireEvent.change(screen.getByLabelText("Ask about your data"), {
      target: { value: "Why did revenue fall?" },
    });
    fireEvent.keyDown(screen.getByLabelText("Ask about your data"), { key: "Enter" });
    expect(await screen.findByText("Why did revenue fall?")).toBeInTheDocument();
    expect(screen.getByText("Analyzing…")).toBeInTheDocument();
    expect(analyticsApi.createRun).toHaveBeenCalledWith({ message: "Why did revenue fall?" });
  });

  it("renders completed assistant response after the completion event", async () => {
    let handler: ((event: PublicRunEvent) => void) | undefined;
    let errorHandler: (() => void) | undefined;
    vi.mocked(analyticsApi.createRun).mockResolvedValue({
      run_id: "run-1",
      conversation_id: "c-1",
      status: "running",
    });
    vi.mocked(analyticsApi.getRun).mockResolvedValue({
      run_id: "run-1",
      conversation_id: "c-1",
      status: "completed",
      created_at: "",
      started_at: "",
      finished_at: "",
      final_response: "## Finding\nRevenue declined.",
      error: null,
      metrics: null,
      charts: [],
    });
    connect.mockImplementation(
      (_id: string, onEvent: (event: PublicRunEvent) => void, onError: () => void) => {
        handler = onEvent;
        errorHandler = onError;
        return { close: vi.fn() } as unknown as EventSource;
      },
    );
    render(<Workbench />);
    fireEvent.change(screen.getByLabelText("Ask about your data"), {
      target: { value: "Analyze revenue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
    await waitFor(() => expect(handler).toBeDefined());
    handler?.({ id: "event-1", run_id: "run-1", type: "run.completed", timestamp: "", data: {} });
    expect(await screen.findByText("Finding")).toBeInTheDocument();
    errorHandler?.();
    expect(screen.getByText("Revenue declined.")).toBeInTheDocument();
    expect(screen.getAllByText("Revenue declined.")).toHaveLength(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a backend error without adding an assistant response", async () => {
    vi.mocked(analyticsApi.createRun).mockRejectedValue(
      new ApiError("The analyst backend is unavailable."),
    );
    render(<Workbench />);
    fireEvent.change(screen.getByLabelText("Ask about your data"), {
      target: { value: "Analyze revenue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The analyst backend is unavailable.",
    );
  });

  it("explains when a run is waiting for a protected-action approval", async () => {
    let handler: ((event: PublicRunEvent) => void) | undefined;
    vi.mocked(analyticsApi.createRun).mockResolvedValue({
      run_id: "run-approval",
      conversation_id: "c-1",
      status: "running",
    });
    vi.mocked(analyticsApi.getRun).mockResolvedValue({
      run_id: "run-approval",
      conversation_id: "c-1",
      status: "waiting_for_approval",
      created_at: "",
      started_at: "",
      finished_at: "",
      final_response: null,
      error: null,
      metrics: null,
      charts: [],
    });
    vi.mocked(approvalsApi.list).mockResolvedValue([
      {
        id: "approval-1",
        run_id: "run-approval",
        agent_name: "primary",
        capability: "filesystem.write",
        tool_name: "write_file",
        resource: "report.md",
        argument_summary: {},
        reason: "This sensitive action requires human approval.",
        status: "pending",
        created_at: "",
        expires_at: null,
        action_fingerprint: "fp",
        parent_run_id: null,
        policy_id: "security.filesystem_write",
        resolved_at: null,
      },
    ]);
    connect.mockImplementation((_id: string, onEvent: (event: PublicRunEvent) => void) => {
      handler = onEvent;
      return { close: vi.fn() } as unknown as EventSource;
    });
    render(<Workbench />);
    fireEvent.change(screen.getByLabelText("Ask about your data"), {
      target: { value: "Create a report" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
    await waitFor(() => expect(handler).toBeDefined());

    handler?.({
      id: "event-approval",
      run_id: "run-approval",
      type: "run.completed",
      timestamp: "",
      data: {},
    });

    expect(await screen.findByRole("region", { name: "Approval required" })).toHaveTextContent(
      "write_file",
    );
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.queryByText("The analyst run ended without an answer.")).not.toBeInTheDocument();
  });

  it("loads and switches persisted conversations", async () => {
    vi.mocked(conversationsApi.list).mockResolvedValue({
      items: [{ id: "old", title: "April revenue decline", created_at: "", updated_at: "" }],
      total: 1,
      limit: 30,
      offset: 0,
    });
    vi.mocked(conversationsApi.get).mockResolvedValue({
      id: "old",
      title: "April revenue decline",
      created_at: "",
      updated_at: "",
      messages: [
        { id: "m1", role: "user", content: "Old question", created_at: "", run_id: null },
        { id: "m2", role: "assistant", content: "Old answer", created_at: "", run_id: "run-old" },
      ],
      messages_total: 2,
      messages_limit: 100,
      messages_offset: 0,
      runs: [],
    });
    render(<Workbench />);
    const item = await screen.findByRole("button", { name: "April revenue decline" });
    fireEvent.click(item);
    expect(await screen.findByText("Old answer")).toBeInTheDocument();
    expect(conversationsApi.get).toHaveBeenCalledWith("old");
  });

  it("creates a clean conversation", async () => {
    vi.mocked(conversationsApi.create).mockResolvedValue({
      id: "new",
      title: "New conversation",
      created_at: "",
      updated_at: "",
    });
    render(<Workbench />);
    fireEvent.click(screen.getByRole("button", { name: /new conversation/i }));
    await waitFor(() => expect(conversationsApi.create).toHaveBeenCalled());
  });

  it("paginates the sidebar and deletes a conversation from its options menu", async () => {
    const firstPage = Array.from({ length: 8 }, (_, index) => ({
      id: `c-${index}`,
      title: `Conversation ${index}`,
      created_at: "",
      updated_at: "",
    }));
    const secondPage = Array.from({ length: 2 }, (_, index) => ({
      id: `c-${index + 8}`,
      title: `Conversation ${index + 8}`,
      created_at: "",
      updated_at: "",
    }));
    vi.mocked(conversationsApi.list)
      .mockResolvedValueOnce({ items: firstPage, total: 10, limit: 8, offset: 0 })
      .mockResolvedValueOnce({ items: secondPage, total: 10, limit: 8, offset: 8 });
    vi.mocked(conversationsApi.remove).mockResolvedValue(undefined);
    render(<Workbench />);
    expect(await screen.findByText("Conversation 0")).toBeInTheDocument();
    expect(screen.queryByText("Conversation 9")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show more (2)" }));
    expect(await screen.findByText("Conversation 9")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Conversation options for Conversation 0" }),
    );
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Confirm delete" }));
    await waitFor(() => expect(conversationsApi.remove).toHaveBeenCalledWith("c-0"));
    expect(screen.queryByText("Conversation 0")).not.toBeInTheDocument();
  });
});
