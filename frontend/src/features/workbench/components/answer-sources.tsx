import type { AnswerSource } from "@/types/analytics";

/** Describe one source the way a reader would check it, without exposing SQL. */
function describe(source: AnswerSource): string {
  const parts: string[] = [];
  if (source.referenced_tables.length) parts.push(source.referenced_tables.join(", "));
  if (source.row_count !== null) {
    parts.push(`${source.row_count.toLocaleString()} row${source.row_count === 1 ? "" : "s"}`);
  }
  if (source.truncated) parts.push("result truncated");
  if (source.executed_at) parts.push(new Date(source.executed_at).toLocaleString());
  return parts.join(" · ");
}

/**
 * The evidence an answer cites.
 *
 * Every chip names a query this run actually executed — the runtime drops
 * references it cannot account for. That is provenance, not verification: it
 * shows which query the analyst pointed at, not that the number came from it.
 * The note says so rather than letting the chips imply more than they check.
 */
export function AnswerSources({ sources }: { sources: AnswerSource[] }) {
  if (!sources.length) return null;
  return (
    <aside className="answer-sources" aria-label="Evidence this answer cites">
      <ul>
        <li className="answer-sources-lead">Based on</li>
        {sources.map((source) => (
          <li key={`${source.run_id}:${source.id}`}>
            <span className="source-chip" title={describe(source)}>
              <span className="source-chip-id">{source.id}</span>
              <span className="source-chip-label">{source.label}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="answer-sources-note">
        Cited by the analyst. Each names a query this run ran, not a check that the figure came from
        it.
      </p>
    </aside>
  );
}
