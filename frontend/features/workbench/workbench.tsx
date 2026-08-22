"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChatComposer } from "@/components/chat-composer";
import { SafeMarkdown } from "@/components/markdown";
import { analyticsApi } from "@/lib/api/analytics";
import { conversationsApi } from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/client";
import type { AnalystRun, PublicRunEvent, RunHistory } from "@/types/analytics";
import type { Conversation, ConversationMessage } from "@/types/conversations";
import { RunAnalysis } from "./run-analysis";
import { ArtifactPanel } from "@/components/artifact-panel";
import { DatabaseExplorer } from "@/components/database-explorer";
import { MemoryInspector } from "@/components/memory-inspector";
import { statusFromEvent } from "./status";
import { approvalsApi, type Approval } from "@/lib/api/approvals";
import { ApprovalCard } from "@/components/approval-card";
import { RunChartPreview } from "@/components/run-chart-preview";
import { ChartRenderer } from "@/components/chart-renderer";

type Message = Pick<ConversationMessage, "role" | "content" | "run_id">;
const CONVERSATION_PAGE_SIZE = 8;

function groupConversations(conversations: Conversation[]) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const recent: Conversation[] = [];
  const previous: Conversation[] = [];
  conversations.forEach((conversation) => {
    const updatedAt = new Date(conversation.updated_at);
    (Number.isNaN(updatedAt.getTime()) || updatedAt >= today ? recent : previous).push(
      conversation,
    );
  });
  return [
    { label: "Today", items: recent },
    { label: "Previous", items: previous },
  ].filter((group) => group.items.length > 0);
}

export function Workbench() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [conversationTotal, setConversationTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [menuConversationId, setMenuConversationId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, RunHistory>>({});
  const [eventsByRun, setEventsByRun] = useState<Record<string, PublicRunEvent[]>>({});
  const [loadingTraces, setLoadingTraces] = useState<Record<string, boolean>>({});
  const [approval, setApproval] = useState<Approval | null>(null);
  const [approvalBusy, setApprovalBusy] = useState(false);
  const source = useRef<EventSource | null>(null);
  const terminalRun = useRef<string | null>(null);
  const finishing = useRef(false);
  const conversationGroups = useMemo(() => groupConversations(conversations), [conversations]);

  const loadConversations = async (offset = 0, append = false) => {
    try {
      const page = await conversationsApi.list(CONVERSATION_PAGE_SIZE, offset);
      setConversationTotal(page.total);
      setConversations((current) =>
        append
          ? [
              ...current,
              ...page.items.filter((item) => !current.some((existing) => existing.id === item.id)),
            ]
          : page.items,
      );
      setHistoryError(null);
    } catch {
      setHistoryError("Conversation history could not be loaded.");
    }
  };
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadConversations();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const switchConversation = async (id: string) => {
    source.current?.close();
    terminalRun.current = null;
    finishing.current = false;
    setStatus(null);
    setError(null);
    try {
      const conversation = await conversationsApi.get(id);
      const historicalRuns = conversation.runs ?? [];
      setConversationId(conversation.id);
      setMessages(
        conversation.messages.map((message) => ({
          role: message.role,
          content: message.content,
          run_id: message.run_id,
        })),
      );
      setRuns(Object.fromEntries(historicalRuns.map((run) => [run.run_id, run])));
      setLoadingTraces(Object.fromEntries(historicalRuns.map((run) => [run.run_id, true])));
      const histories = await Promise.all(
        historicalRuns.map(
          async (run) =>
            [
              run.run_id,
              await analyticsApi
                .getEvents(run.run_id)
                .then((result) => result.items)
                .catch(() => []),
            ] as const,
        ),
      );
      setEventsByRun(Object.fromEntries(histories));
      setLoadingTraces({});
    } catch {
      setHistoryError("Conversation could not be loaded.");
    }
  };
  const finish = async (runId: string) => {
    if (finishing.current) return;
    finishing.current = true;
    let run: AnalystRun | undefined;
    for (let attempt = 0; attempt < 8; attempt += 1) {
      run = await analyticsApi.getRun(runId);
      if (run.status !== "running") break;
      await new Promise((resolve) => window.setTimeout(resolve, 100));
    }
    if (!run) throw new Error("The run result was unavailable.");
    setRuns((current) => ({
      ...current,
      [runId]: {
        run_id: run.run_id,
        status: run.status,
        created_at: run.created_at,
        started_at: run.started_at,
        completed_at: run.finished_at,
        error: run.error,
        metrics: run.metrics,
        charts: run.charts ?? [],
      },
    }));
    if (run.status === "completed" && run.final_response)
      setMessages((current) => [
        ...current,
        { role: "assistant", content: run.final_response!, run_id: runId },
      ]);
    else if (run.status === "waiting_for_approval") {
      const pending = (await approvalsApi.list(runId)).find((item) => item.status === "pending");
      setApproval(pending ?? null);
      setError(
        pending ? null : "The analyst is waiting for approval before making a protected change.",
      );
    } else setError(run.error ?? "The analyst run ended without an answer.");
    setStatus(null);
    source.current?.close();
    source.current = null;
    void loadConversations();
  };
  const submit = async (message: string) => {
    terminalRun.current = null;
    finishing.current = false;
    setApproval(null);
    setError(null);
    setStatus("Analyzing…");
    setMessages((current) => [...current, { role: "user", content: message, run_id: null }]);
    try {
      const created = await analyticsApi.createRun({
        message,
        ...(conversationId ? { conversation_id: conversationId } : {}),
      });
      setConversationId(created.conversation_id);
      void loadConversations();
      setRuns((current) => ({
        ...current,
        [created.run_id]: {
          run_id: created.run_id,
          status: "running",
          created_at: "",
          started_at: null,
          completed_at: null,
          error: null,
          metrics: null,
          charts: [],
        },
      }));
      setEventsByRun((current) => ({ ...current, [created.run_id]: [] }));
      source.current = analyticsApi.connect(
        created.run_id,
        (event: PublicRunEvent) => {
          setEventsByRun((current) => ({
            ...current,
            [created.run_id]: current[created.run_id]?.some((existing) => existing.id === event.id)
              ? current[created.run_id]
              : [...(current[created.run_id] ?? []), event],
          }));
          setStatus(statusFromEvent(event));
          if (event.type === "run.completed") {
            terminalRun.current = created.run_id;
            void finish(created.run_id);
          }
          if (event.type === "run.failed") {
            terminalRun.current = created.run_id;
            setError(
              typeof event.data.error === "string" ? event.data.error : "The analyst run failed.",
            );
            setStatus(null);
            source.current?.close();
            void loadConversations();
          }
        },
        () => {
          if (terminalRun.current === created.run_id) return;
          setError("The progress stream disconnected. Checking the run status…");
          void finish(created.run_id).catch(() => setStatus(null));
        },
      );
    } catch (cause) {
      setStatus(null);
      setError(cause instanceof ApiError ? cause.message : "Unable to start the analyst run.");
    }
  };
  const newConversation = async () => {
    source.current?.close();
    terminalRun.current = null;
    finishing.current = false;
    setMessages([]);
    setRuns({});
    setEventsByRun({});
    setApproval(null);
    setStatus(null);
    setError(null);
    try {
      const conversation = await conversationsApi.create();
      setConversationId(conversation.id);
      setConversationTotal((total) => total + 1);
      setConversations((current) =>
        [conversation, ...current.filter((item) => item.id !== conversation.id)].slice(
          0,
          CONVERSATION_PAGE_SIZE,
        ),
      );
    } catch {
      setHistoryError("A new conversation could not be created.");
    }
  };
  const showMoreConversations = async () => {
    setLoadingMore(true);
    try {
      await loadConversations(conversations.length, true);
    } finally {
      setLoadingMore(false);
    }
  };
  const renameConversation = async (conversation: Conversation) => {
    const title = window.prompt("Rename conversation", conversation.title)?.trim();
    if (!title || title === conversation.title) return;
    try {
      const updated = await conversationsApi.rename(conversation.id, title);
      setConversations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch {
      setHistoryError("Conversation could not be renamed.");
    } finally {
      setMenuConversationId(null);
    }
  };
  const deleteConversation = async (conversation: Conversation) => {
    if (confirmDeleteId !== conversation.id) {
      setConfirmDeleteId(conversation.id);
      return;
    }
    try {
      await conversationsApi.remove(conversation.id);
      setConversations((current) => current.filter((item) => item.id !== conversation.id));
      setConversationTotal((total) => Math.max(0, total - 1));
      setMenuConversationId(null);
      setConfirmDeleteId(null);
      if (conversationId === conversation.id) {
        source.current?.close();
        setConversationId(null);
        setMessages([]);
        setRuns({});
        setEventsByRun({});
        setStatus(null);
        setError(null);
      }
    } catch {
      setHistoryError("Conversation could not be deleted.");
    }
  };

  return (
    <main className="workbench">
      <aside className="sidebar">
        <div>
          <span className="eyebrow">WORKBENCH</span>
          <h1>AI Data Analyst</h1>
        </div>
        <button className="new-conversation" onClick={() => void newConversation()}>
          ＋ New conversation
        </button>
        <section>
          <p>CONVERSATIONS</p>
          {historyError && (
            <span className="muted" role="alert">
              {historyError}
            </span>
          )}
          {!historyError && conversations.length === 0 && (
            <span className="muted">No saved conversations yet.</span>
          )}
          <nav className="conversation-groups" aria-label="Conversations">
            {conversationGroups.map((group) => (
              <div className="conversation-group" key={group.label}>
                <h3>{group.label}</h3>
                <div className="conversation-list">
                  {group.items.map((conversation) => (
                    <div
                      className={`conversation-item ${conversation.id === conversationId ? "active" : ""}`}
                      key={conversation.id}
                    >
                      <button
                        className="conversation-select"
                        onClick={() => void switchConversation(conversation.id)}
                        title={conversation.title}
                      >
                        {conversation.title}
                      </button>
                      <div className="conversation-menu-wrap">
                        <button
                          className="conversation-menu-toggle"
                          aria-label={`Conversation options for ${conversation.title}`}
                          aria-expanded={menuConversationId === conversation.id}
                          onClick={() => {
                            setConfirmDeleteId(null);
                            setMenuConversationId((current) =>
                              current === conversation.id ? null : conversation.id,
                            );
                          }}
                        >
                          •••
                        </button>
                        {menuConversationId === conversation.id && (
                          <div className="conversation-menu" role="menu">
                            <button
                              role="menuitem"
                              onClick={() => void renameConversation(conversation)}
                            >
                              Rename
                            </button>
                            <button
                              role="menuitem"
                              className="delete-conversation"
                              onClick={() => void deleteConversation(conversation)}
                            >
                              {confirmDeleteId === conversation.id ? "Confirm delete" : "Delete"}
                            </button>
                            {confirmDeleteId === conversation.id && (
                              <button role="menuitem" onClick={() => setConfirmDeleteId(null)}>
                                Cancel
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </nav>
          {!historyError && conversations.length < conversationTotal && (
            <button
              className="show-more-conversations"
              onClick={() => void showMoreConversations()}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading…" : `Show more (${conversationTotal - conversations.length})`}
            </button>
          )}
        </section>
        <ArtifactPanel
          runIds={Object.keys(runs)}
          refreshKey={Object.values(runs)
            .map((run) => `${run.run_id}:${run.status}:${run.completed_at ?? ""}`)
            .join(",")}
        />
        <DatabaseExplorer />
        {process.env.NEXT_PUBLIC_DEVELOPER_MODE === "true" && <MemoryInspector />}
      </aside>
      <section className="conversation">
        <header>
          <div>
            <span className="eyebrow">ANALYSIS SESSION</span>
            <h2>AI Data Analyst</h2>
          </div>
          <span className="connection">● Backend connected</span>
        </header>
        <div className="messages" aria-live="polite">
          {messages.length === 0 && !status && (
            <div className="empty">
              <h3>Ask a question about your data</h3>
              <p>
                Try investigating revenue changes, customer behavior, conversion, or operational
                performance.
              </p>
            </div>
          )}
          {messages.map((message, index) => (
            <div className="message-with-analysis" key={`${message.run_id ?? "message"}-${index}`}>
              <article
                className={`message ${message.role}`}
                data-run-id={message.run_id ?? undefined}
              >
                {message.role === "assistant" ? (
                  <SafeMarkdown content={message.content} />
                ) : (
                  message.content
                )}
              </article>
              {message.role === "assistant" &&
                message.run_id &&
                runs[message.run_id]?.charts?.map((chart) => (
                  <ChartRenderer key={chart.id} chart={chart} />
                ))}
              {message.role === "assistant" &&
                message.run_id &&
                !runs[message.run_id]?.charts?.length && <RunChartPreview runId={message.run_id} />}
              {message.role === "assistant" && message.run_id && (
                <RunAnalysis
                  run={runs[message.run_id]}
                  events={eventsByRun[message.run_id] ?? []}
                  loading={loadingTraces[message.run_id]}
                />
              )}
            </div>
          ))}
          {status && (
            <div className="progress">
              <span className="spinner" />
              {status}
            </div>
          )}
          {approval && (
            <ApprovalCard
              approval={approval}
              busy={approvalBusy}
              onApprove={() => {
                setApprovalBusy(true);
                void approvalsApi
                  .approve(approval.id)
                  .then(() => {
                    finishing.current = false;
                    setApproval(null);
                    return finish(approval.run_id);
                  })
                  .catch(() => setError("Approval could not be completed."))
                  .finally(() => setApprovalBusy(false));
              }}
              onReject={() => {
                setApprovalBusy(true);
                void approvalsApi
                  .reject(approval.id)
                  .then(() => {
                    finishing.current = false;
                    setApproval(null);
                    return finish(approval.run_id);
                  })
                  .catch(() => setError("Approval could not be completed."))
                  .finally(() => setApprovalBusy(false));
              }}
            />
          )}
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
        </div>
        <ChatComposer onSubmit={submit} disabled={Boolean(status)} />
      </section>
    </main>
  );
}
