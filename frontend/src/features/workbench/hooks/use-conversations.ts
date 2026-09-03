"use client";

import { useCallback, useMemo, useState } from "react";
import { conversationsApi } from "@/lib/api/conversations";
import type { Conversation } from "@/types/conversations";

export const CONVERSATION_PAGE_SIZE = 8;

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

/**
 * The conversation sidebar: paging, selection, and rename/delete.
 *
 * Deleting the open conversation also has to clear the transcript, which this
 * hook does not own, so `remove` reports whether that happened and the caller
 * decides what to reset.
 */
export function useConversations(workspaceId: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const groups = useMemo(() => groupConversations(conversations), [conversations]);

  const load = useCallback(
    async (offset = 0, append = false) => {
      try {
        const page = await conversationsApi.list(workspaceId, CONVERSATION_PAGE_SIZE, offset);
        setTotal(page.total);
        setConversations((current) =>
          append
            ? [
                ...current,
                ...page.items.filter((item) => !current.some((existing) => existing.id === item.id)),
              ]
            : page.items,
        );
        setError(null);
      } catch {
        setError("Conversation history could not be loaded.");
      }
    },
    [workspaceId],
  );

  const showMore = useCallback(async () => {
    setLoadingMore(true);
    try {
      await load(conversations.length, true);
    } finally {
      setLoadingMore(false);
    }
  }, [conversations.length, load]);

  const create = useCallback(async () => {
    try {
      const conversation = await conversationsApi.create(workspaceId);
      setConversationId(conversation.id);
      setTotal((current) => current + 1);
      setConversations((current) =>
        [conversation, ...current.filter((item) => item.id !== conversation.id)].slice(
          0,
          CONVERSATION_PAGE_SIZE,
        ),
      );
    } catch {
      setError("A new conversation could not be created.");
    }
  }, [workspaceId]);

  const rename = useCallback(
    async (conversation: Conversation) => {
      const title = window.prompt("Rename conversation", conversation.title)?.trim();
      if (!title || title === conversation.title) return;
      try {
        const updated = await conversationsApi.rename(workspaceId, conversation.id, title);
        setConversations((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        );
      } catch {
        setError("Conversation could not be renamed.");
      } finally {
        setMenuId(null);
      }
    },
    [workspaceId],
  );

  /** Returns true when the deleted conversation was the one on screen. */
  const remove = useCallback(
    async (conversation: Conversation): Promise<boolean> => {
      if (confirmDeleteId !== conversation.id) {
        setConfirmDeleteId(conversation.id);
        return false;
      }
      try {
        await conversationsApi.remove(workspaceId, conversation.id);
        setConversations((current) => current.filter((item) => item.id !== conversation.id));
        setTotal((current) => Math.max(0, current - 1));
        setMenuId(null);
        setConfirmDeleteId(null);
        if (conversationId === conversation.id) {
          setConversationId(null);
          return true;
        }
      } catch {
        setError("Conversation could not be deleted.");
      }
      return false;
    },
    [confirmDeleteId, conversationId, workspaceId],
  );

  return {
    conversations,
    groups,
    conversationId,
    setConversationId,
    total,
    error,
    setError,
    loadingMore,
    menuId,
    setMenuId,
    confirmDeleteId,
    setConfirmDeleteId,
    load,
    showMore,
    create,
    rename,
    remove,
  };
}
