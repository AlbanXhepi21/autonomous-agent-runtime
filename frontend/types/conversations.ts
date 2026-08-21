export interface Conversation { id: string; title: string; created_at: string; updated_at: string; }
export interface ConversationMessage { id: string; role: "user" | "assistant"; content: string; created_at: string; run_id: string | null; }
export interface ConversationList { items: Conversation[]; total: number; limit: number; offset: number; }
import type { RunHistory } from "@/types/analytics";

export interface ConversationDetail extends Conversation { messages: ConversationMessage[]; messages_total: number; messages_limit: number; messages_offset: number; runs?: RunHistory[]; }
