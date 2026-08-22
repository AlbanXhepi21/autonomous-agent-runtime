import type { PublicRunEvent } from "@/types/analytics";

export function statusFromEvent(event: PublicRunEvent): string {
  if (event.type.startsWith("schema.")) return "Inspecting database…";
  if (event.type.startsWith("sql.query"))
    return event.type === "sql.query_completed" ? "Comparing results…" : "Running query…";
  if (event.type.startsWith("python.")) return "Analyzing results…";
  if (event.type === "agent.completed") return "Preparing answer…";
  return "Analyzing…";
}
