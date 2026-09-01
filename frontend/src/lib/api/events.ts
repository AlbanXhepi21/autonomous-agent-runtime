/**
 * The public run-event vocabulary, mirroring `_PUBLIC_EVENT_TYPES` in
 * app/api/run_manager.py plus the two synthesised `agent.*` events.
 *
 * This is the only place the names are listed. The stream subscribes to every
 * entry, so an event the server projects can never be silently dropped by the
 * live connection while still appearing in replayed history.
 */
export const PUBLIC_RUN_EVENT_TYPES = [
  "run.started",
  "run.completed",
  "run.failed",
  "agent.started",
  "agent.completed",
  "skill.loaded",
  "schema.tables_listed",
  "schema.table_described",
  "sql.query_started",
  "sql.query_completed",
  "sql.query_failed",
  "sql.query_rejected",
  "python.analysis_started",
  "python.analysis_completed",
  "artifact.created",
  "chart.created",
  "report.created",
  "plan.updated",
  "delegation.started",
  "delegation.completed",
  "tool.started",
  "tool.completed",
  "tool.failed",
  "security.policy_evaluated",
] as const;

export type PublicRunEventType = (typeof PUBLIC_RUN_EVENT_TYPES)[number];
