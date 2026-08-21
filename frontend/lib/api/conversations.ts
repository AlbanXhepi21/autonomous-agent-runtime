import { request } from "@/lib/api/client";
import type { Conversation, ConversationDetail, ConversationList } from "@/types/conversations";

export const conversationsApi = {
  create: (title = "New conversation") => request<Conversation>("/api/v1/conversations", { method: "POST", body: JSON.stringify({ title }) }),
  list: (limit = 30, offset = 0) => request<ConversationList>(`/api/v1/conversations?limit=${limit}&offset=${offset}`),
  get: (id: string, messageLimit = 100, messageOffset = 0) => request<ConversationDetail>(`/api/v1/conversations/${id}?message_limit=${messageLimit}&message_offset=${messageOffset}`),
  rename: (id: string, title: string) => request<Conversation>(`/api/v1/conversations/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  remove: (id: string) => request<void>(`/api/v1/conversations/${id}`, { method: "DELETE" }),
};
