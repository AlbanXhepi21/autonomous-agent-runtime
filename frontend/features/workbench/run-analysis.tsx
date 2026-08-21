"use client";

import { useMemo, useState } from "react";
import type { PublicRunEvent, RunHistory, RunMetrics } from "@/types/analytics";

type Filter = "all" | "sql" | "tools" | "artifacts" | "errors";

const FILTERS: Array<[Filter, string]> = [["all", "All"], ["sql", "SQL"], ["tools", "Tools"], ["artifacts", "Artifacts"], ["errors", "Errors"]];

function eventFilter(event: PublicRunEvent, filter: Filter) {
  // Query-started, failed, and rejected events are execution noise. The Workbench
  // presents only completed queries because those are the queries used as evidence.
  if (event.type.startsWith("sql.") && event.type !== "sql.query_completed") return false;
  if (filter === "all") return true;
  if (filter === "sql") return event.type.startsWith("sql.");
  if (filter === "tools") return event.type.startsWith("tool.") || event.type.startsWith("schema.") || event.type.startsWith("python.") || event.type.startsWith("delegation.");
  if (filter === "artifacts") return event.type.includes("artifact") || event.type.includes("chart") || event.type.includes("report");
  return event.type.includes("failed") || event.type.includes("rejected") || event.type.startsWith("security.");
}

function eventText(event: PublicRunEvent) {
  const data = event.data;
  if (event.type === "skill.loaded") return `Data analysis skill loaded${typeof data.skill === "string" ? `: ${data.skill}` : ""}`;
  if (event.type === "schema.table_described") return `Inspected ${(Array.isArray(data.tables) ? data.tables : []).join(", ") || "table"}`;
  if (event.type === "schema.tables_listed") return "Inspected available tables";
  if (event.type === "sql.query_started") return `Running ${queryLabel(event)}`;
  if (event.type === "sql.query_completed") return `${queryLabel(event)} completed`;
  if (event.type === "sql.query_failed") return `${queryLabel(event)} failed`;
  if (event.type === "sql.query_rejected") return `${queryLabel(event)} rejected by SQL safety policy`;
  if (event.type === "python.analysis_started") return "Python analysis started";
  if (event.type === "python.analysis_completed") return "Python analysis completed";
  if (event.type === "artifact.created" || event.type === "chart.created" || event.type === "report.created") return "Artifact created";
  if (event.type === "delegation.started") return `Delegated analysis${typeof data.agent_name === "string" ? ` → ${data.agent_name}` : ""}`;
  if (event.type === "delegation.completed") return "Delegated analysis completed";
  if (event.type === "security.policy_evaluated") return data.decision === "deny" ? "Tool denied by capability policy" : "Security policy evaluated";
  if (event.type === "tool.completed") return `${toolName(data)} completed`;
  if (event.type === "tool.failed") return `${toolName(data)} failed`;
  if (event.type === "run.completed") return "Analysis completed";
  if (event.type === "run.failed") return "Analysis failed";
  return event.type.replace(/[._]/g, " ");
}

function queryLabel(event: PublicRunEvent) { return `Query #${typeof event.data.query_id === "string" ? event.data.query_id.replace(/^query_?0*/, "") || event.data.query_id : "?"}`; }
function toolName(data: Record<string, unknown>) { return typeof data.tool_name === "string" ? data.tool_name.replaceAll("_", " ") : "Tool"; }
function isFailure(event: PublicRunEvent) { return event.type.includes("failed") || event.type.includes("rejected") || (event.type === "security.policy_evaluated" && event.data.decision === "deny"); }
function metric(value: string | number | null | undefined) { return value === null || value === undefined ? "—" : value; }

function Metrics({ metrics }: { metrics: RunMetrics | null | undefined }) {
  if (!metrics) return null;
  return <dl className="run-metrics"><div><dt>Duration</dt><dd>{metric(metrics.total_duration_ms === null ? null : `${metrics.total_duration_ms}ms`)}</dd></div><div><dt>Iterations</dt><dd>{metrics.iterations}</dd></div><div><dt>SQL queries</dt><dd>{metrics.database_query_count}</dd></div><div><dt>Tool calls</dt><dd>{metrics.tool_calls}</dd></div><div><dt>Tokens</dt><dd>{metric(metrics.total_tokens)}</dd></div><div><dt>Estimated cost</dt><dd title={metrics.estimated_cost === null ? "Configure OpenAI per-million token prices on the backend to calculate this." : undefined}>{metrics.estimated_cost === null ? "Not configured" : `$${metrics.estimated_cost.toFixed(4)}`}</dd></div></dl>;
}

export function RunAnalysis({ run, events, loading }: { run: RunHistory | undefined; events: PublicRunEvent[]; loading?: boolean }) {
  const [open, setOpen] = useState(false); const [filter, setFilter] = useState<Filter>("all");
  const visible = useMemo(() => events.filter((event) => eventFilter(event, filter)), [events, filter]);
  return <section className="run-analysis"><button className="analysis-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>{open ? "⌄" : "›"} View analysis</button>{open && <div className="analysis-body"><div className="analysis-heading"><div><span className="eyebrow">ANALYSIS RUN</span><strong>{run?.status === "failed" ? "Failed" : run?.status === "running" ? "Running" : "Completed"}</strong></div><Metrics metrics={run?.metrics} /></div><div className="trace-filters">{FILTERS.map(([value, label]) => <button key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{label}</button>)}</div>{loading && <p className="trace-empty">Loading structured trace…</p>}{!loading && visible.length === 0 && <p className="trace-empty">No public trace events are available for this run.</p>}<ol className="trace-events">{visible.map((event) => <li key={event.id} className={isFailure(event) ? "failure" : ""}><span className="trace-icon">{isFailure(event) ? "⚠" : event.type.endsWith("started") ? "●" : "✓"}</span><div><strong>{eventText(event)}</strong>{event.type.startsWith("sql.") && <div className="query-details"><span>Status: {event.type === "sql.query_completed" ? "Completed" : event.type === "sql.query_failed" ? "Failed" : event.type === "sql.query_rejected" ? "Rejected" : "Running"}</span>{typeof event.data.duration_ms === "number" && <span>Duration: {event.data.duration_ms}ms</span>}{typeof event.data.row_count === "number" && <span>Rows: {event.data.row_count}</span>}{Array.isArray(event.data.referenced_tables) && event.data.referenced_tables.length > 0 && <span>Tables: {event.data.referenced_tables.join(", ")}</span>}<details><summary>SQL</summary><p>{typeof event.data.sql === "string" ? <code>{event.data.sql}</code> : "SQL is not retained or exposed for this run."}</p></details></div>}{typeof event.data.error === "string" && <p className="trace-reason">Reason: {event.data.error}</p>}</div></li>)}</ol></div>}</section>;
}
