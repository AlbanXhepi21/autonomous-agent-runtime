export type RunStatus = "running" | "completed" | "failed" | "waiting_for_approval";
import type { ChartSpec } from "@/types/displays";

export interface CreateRunRequest { message: string; conversation_id?: string; }
export interface CreateRunResponse { run_id: string; conversation_id: string; status: "running"; }
export interface RunMetrics { iterations: number; tool_calls: number; delegations: number; total_duration_ms: number | null; database_query_count: number; database_rows_returned: number; database_rejected_query_count: number; total_tokens: number | null; estimated_cost: number | null; }
export interface AnalystRun { run_id: string; conversation_id: string; status: RunStatus; created_at: string; started_at: string | null; finished_at: string | null; final_response: string | null; error: string | null; metrics: RunMetrics | null; charts?: ChartSpec[]; }
export interface PublicRunEvent { id: string; run_id: string; type: string; timestamp: string; data: Record<string, unknown>; }
export interface RunHistory { run_id: string; status: RunStatus; created_at: string; started_at: string | null; completed_at: string | null; error: string | null; metrics: RunMetrics | null; charts?: ChartSpec[]; }
