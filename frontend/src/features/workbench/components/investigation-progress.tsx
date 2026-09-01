"use client";

import { latestPlanUpdate } from "@/features/workbench/investigation-plan";
import type { PublicRunEvent } from "@/types/analytics";

const REQUEST_CLASS_LABELS: Record<string, string> = {
  simple_fact: "Simple fact",
  comparison: "Comparison",
  investigation: "Investigation",
  executive_report: "Executive report",
  detailed_report: "Detailed report",
};

/**
 * A compact, read-only view of the run's own investigation plan, built purely
 * from the `plan.updated` events the runtime already reconciled against real
 * evidence. Nothing here recomputes a status or a count; it only displays the
 * latest snapshot the server sent.
 */
export function InvestigationProgress({ events }: { events: PublicRunEvent[] }) {
  const update = latestPlanUpdate(events);
  if (!update) return null;
  const { plan, progress } = update;
  const blocked = progress.questions_blocked + progress.outputs_blocked;

  return (
    <div className="investigation-progress" aria-label="Investigation plan progress">
      <div className="investigation-progress-heading">
        <span className="investigation-progress-class">
          {REQUEST_CLASS_LABELS[plan.request_class] ?? plan.request_class}
        </span>
        <span className="investigation-progress-objective">{plan.objective}</span>
      </div>
      <dl className="investigation-progress-stats">
        <div>
          <dt>Questions</dt>
          <dd>
            {progress.questions_answered}/{progress.questions_total} answered
          </dd>
        </div>
        <div>
          <dt>Outputs</dt>
          <dd>
            {progress.outputs_created}/{progress.outputs_required} created
          </dd>
        </div>
        <div>
          <dt>Displays</dt>
          <dd>
            {progress.outputs_created} / {progress.maximum_displays} budget
          </dd>
        </div>
        {blocked > 0 && (
          <div>
            <dt>Blocked</dt>
            <dd>{blocked}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
