import { describe, expect, it } from "vitest";
import { latestPlanUpdate } from "@/features/workbench/investigation-plan";
import type { PublicRunEvent } from "@/types/analytics";

const PLAN = {
  objective: "Analyze payment failures in 2026",
  request_class: "executive_report",
  questions: [
    { id: "q1", question: "What is the total failure volume?", status: "answered", evidence_ids: ["query_001"] },
    { id: "q2", question: "What is the breakdown by reason?", status: "pending", evidence_ids: [] },
  ],
  outputs: [
    { id: "o1", kind: "kpi", purpose: "Total failures", required: true, status: "created", display_id: "c1" },
    { id: "o2", kind: "table", purpose: "Supporting rows", required: false, status: "blocked", display_id: null },
  ],
  completion_criteria: ["State the total with evidence."],
  maximum_displays: 6,
};

const PROGRESS = {
  questions_answered: 1,
  questions_blocked: 0,
  questions_total: 2,
  outputs_created: 1,
  outputs_blocked: 1,
  outputs_required: 1,
  outputs_total: 2,
  maximum_displays: 6,
};

function planEvent(id: string, overrides: Partial<{ plan: unknown; progress: unknown }> = {}): PublicRunEvent {
  return {
    id,
    run_id: "r1",
    type: "plan.updated",
    timestamp: "2026-01-01T00:00:00Z",
    data: { plan: PLAN, progress: PROGRESS, ...overrides },
  };
}

describe("latestPlanUpdate", () => {
  it("returns null when the run never planned", () => {
    expect(latestPlanUpdate([])).toBeNull();
    expect(
      latestPlanUpdate([
        { id: "e1", run_id: "r1", type: "run.started", timestamp: "", data: {} },
      ]),
    ).toBeNull();
  });

  it("returns the most recent plan snapshot", () => {
    const older = planEvent("e1", { plan: { ...PLAN, objective: "Older objective" } });
    const newer = planEvent("e2");

    const result = latestPlanUpdate([older, newer]);

    expect(result?.plan.objective).toBe("Analyze payment failures in 2026");
    expect(result?.progress.questions_answered).toBe(1);
  });

  it("ignores a malformed payload rather than throwing", () => {
    const malformed = planEvent("e1", { plan: { objective: "Missing fields" } });

    expect(latestPlanUpdate([malformed])).toBeNull();
  });
});
