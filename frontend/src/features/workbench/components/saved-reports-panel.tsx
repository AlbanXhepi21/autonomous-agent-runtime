"use client";

import { useEffect } from "react";
import { useSavedReports } from "@/features/workbench/hooks/use-saved-reports";
import { SavedReportDetail } from "@/features/workbench/components/saved-report-detail";
import { useWorkspaceId } from "@/features/workbench/workspace-context";

/**
 * The saved-reports sidebar: durable recipes, reopened and rerun on demand.
 *
 * Distinct from Generated Outputs below it — this lists recipes that can be
 * executed again, not the documents an execution already produced.
 */
export function SavedReportsPanel({ refreshKey }: { refreshKey?: string }) {
  const workspaceId = useWorkspaceId();
  const state = useSavedReports(workspaceId);
  const { items, total, statusFilter, error, load, select, close } = state;

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  return (
    <>
      <aside className="artifact-panel saved-reports-panel">
        <h2>
          Saved Reports <small>({total})</small>
        </h2>
        <div className="report-refresh-row">
          <button
            type="button"
            aria-pressed={statusFilter === "active"}
            className={statusFilter === "active" ? "active" : ""}
            onClick={() => void load("active")}
          >
            Active
          </button>
          <button
            type="button"
            aria-pressed={statusFilter === "archived"}
            className={statusFilter === "archived" ? "active" : ""}
            onClick={() => void load("archived")}
          >
            Archived
          </button>
        </div>
        {error && (
          <span className="muted" role="alert">
            {error}
          </span>
        )}
        {!error && items.length === 0 && <p>No saved reports yet.</p>}
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <button onClick={() => void select(item.id)} title={item.description ?? undefined}>
                {item.name}
              </button>
              <span className="muted">{item.template_id}</span>
            </li>
          ))}
        </ul>
      </aside>
      {state.selectedId && <SavedReportDetail state={state} onClose={close} />}
    </>
  );
}
