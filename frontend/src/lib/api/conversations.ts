import { request } from "@/lib/api/client";
import type { Conversation, ConversationDetail, ConversationList } from "@/types/conversations";

const base = (workspaceId: string) => `/api/v1/workspaces/${workspaceId}/conversations`;

export const conversationsApi = {
  create: (workspaceId: string, title = "New conversation") =>
    request<Conversation>(base(workspaceId), {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  list: (workspaceId: string, limit = 30, offset = 0) =>
    request<ConversationList>(`${base(workspaceId)}?limit=${limit}&offset=${offset}`),
  get: (workspaceId: string, id: string, messageLimit = 100, messageOffset = 0) =>
    request<ConversationDetail>(
      `${base(workspaceId)}/${id}?message_limit=${messageLimit}&message_offset=${messageOffset}`,
    ),
  rename: (workspaceId: string, id: string, title: string) =>
    request<Conversation>(`${base(workspaceId)}/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  remove: (workspaceId: string, id: string) =>
    request<void>(`${base(workspaceId)}/${id}`, { method: "DELETE" }),
};
