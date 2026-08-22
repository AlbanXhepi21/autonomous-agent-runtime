"use client";

import { useCallback, useEffect } from "react";
import { ChatComposer } from "@/components/ui/chat-composer";
import { SafeMarkdown } from "@/components/ui/markdown";
import { conversationsApi } from "@/lib/api/conversations";
import { RunAnalysis } from "@/features/workbench/components/run-analysis";
import { ArtifactPanel } from "@/features/workbench/components/artifact-panel";
import { DatabaseExplorer } from "@/features/workbench/components/database-explorer";
import { MemoryInspector } from "@/features/workbench/components/memory-inspector";
import { ApprovalCard } from "@/features/workbench/components/approval-card";
import { RunChartPreview } from "@/features/workbench/components/run-chart-preview";
import { ChartRenderer } from "@/features/workbench/components/chart-renderer";
import { useAgentRun } from "./hooks/use-agent-run";
import { useApprovals } from "./hooks/use-approvals";
import { useConversations } from "./hooks/use-conversations";
import { useWorkbenchConfig } from "./hooks/use-workbench-config";

export function Workbench() {
  const conversations = useConversations();
  const config = useWorkbenchConfig();
  const { load: loadConversations, setConversationId } = conversations;

  const approvals = useApprovals();
  const { loadPending } = approvals;

  const onRunSettled = useCallback(() => void loadConversations(), [loadConversations]);
  const onApprovalRequired = useCallback((runId: string) => loadPending(runId), [loadPending]);

  const run = useAgentRun({ onRunSettled, onApprovalRequired });

  const decide = async (decision: "approve" | "reject") => {
    const released = await approvals.resolve(decision);
    if (released) await run.resume(released);
    else run.setError("Approval could not be completed.");
  };

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const switchConversation = async (id: string) => {
    approvals.setApproval(null);
    try {
      const conversation = await conversationsApi.get(id);
      setConversationId(conversation.id);
      await run.restore(
        conversation.messages.map((message) => ({
          role: message.role,
          content: message.content,
          run_id: message.run_id,
        })),
        conversation.runs ?? [],
      );
    } catch {
      conversations.setError("Conversation could not be loaded.");
    }
  };

  const newConversation = async () => {
    run.reset();
    approvals.setApproval(null);
    await conversations.create();
  };

  const deleteConversation = async (conversation: Parameters<typeof conversations.remove>[0]) => {
    if (await conversations.remove(conversation)) run.reset();
  };

  const submit = (message: string) =>
    run.submit(message, conversations.conversationId, setConversationId);

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
          {conversations.error && (
            <span className="muted" role="alert">
              {conversations.error}
            </span>
          )}
          {!conversations.error && conversations.conversations.length === 0 && (
            <span className="muted">No saved conversations yet.</span>
          )}
          <nav className="conversation-groups" aria-label="Conversations">
            {conversations.groups.map((group) => (
              <div className="conversation-group" key={group.label}>
                <h3>{group.label}</h3>
                <div className="conversation-list">
                  {group.items.map((conversation) => (
                    <div
                      className={`conversation-item ${conversation.id === conversations.conversationId ? "active" : ""}`}
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
                          aria-expanded={conversations.menuId === conversation.id}
                          onClick={() => {
                            conversations.setConfirmDeleteId(null);
                            conversations.setMenuId((current) =>
                              current === conversation.id ? null : conversation.id,
                            );
                          }}
                        >
                          •••
                        </button>
                        {conversations.menuId === conversation.id && (
                          <div className="conversation-menu" role="menu">
                            <button
                              role="menuitem"
                              onClick={() => void conversations.rename(conversation)}
                            >
                              Rename
                            </button>
                            <button
                              role="menuitem"
                              className="delete-conversation"
                              onClick={() => void deleteConversation(conversation)}
                            >
                              {conversations.confirmDeleteId === conversation.id
                                ? "Confirm delete"
                                : "Delete"}
                            </button>
                            {conversations.confirmDeleteId === conversation.id && (
                              <button
                                role="menuitem"
                                onClick={() => conversations.setConfirmDeleteId(null)}
                              >
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
          {!conversations.error && conversations.conversations.length < conversations.total && (
            <button
              className="show-more-conversations"
              onClick={() => void conversations.showMore()}
              disabled={conversations.loadingMore}
            >
              {conversations.loadingMore
                ? "Loading…"
                : `Show more (${conversations.total - conversations.conversations.length})`}
            </button>
          )}
        </section>
        <ArtifactPanel
          runIds={Object.keys(run.runs)}
          refreshKey={Object.values(run.runs)
            .map((item) => `${item.run_id}:${item.status}:${item.completed_at ?? ""}`)
            .join(",")}
        />
        <DatabaseExplorer />
        {config.developer_mode && <MemoryInspector />}
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
          {run.messages.length === 0 && !run.status && (
            <div className="empty">
              <h3>Ask a question about your data</h3>
              <p>
                Try investigating revenue changes, customer behavior, conversion, or operational
                performance.
              </p>
            </div>
          )}
          {run.messages.map((message, index) => (
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
                run.runs[message.run_id]?.charts?.map((chart) => (
                  <ChartRenderer key={chart.id} chart={chart} />
                ))}
              {message.role === "assistant" &&
                message.run_id &&
                !run.runs[message.run_id]?.charts?.length && (
                  <RunChartPreview runId={message.run_id} />
                )}
              {message.role === "assistant" && message.run_id && (
                <RunAnalysis
                  run={run.runs[message.run_id]}
                  events={run.eventsByRun[message.run_id] ?? []}
                  loading={run.loadingTraces[message.run_id]}
                />
              )}
            </div>
          ))}
          {run.status && (
            <div className="progress">
              <span className="spinner" />
              {run.status}
            </div>
          )}
          {approvals.approval && (
            <ApprovalCard
              approval={approvals.approval}
              busy={approvals.busy}
              onApprove={() => void decide("approve")}
              onReject={() => void decide("reject")}
            />
          )}
          {run.error && (
            <div className="error" role="alert">
              {run.error}
            </div>
          )}
        </div>
        <ChatComposer onSubmit={submit} disabled={Boolean(run.status)} />
      </section>
    </main>
  );
}
