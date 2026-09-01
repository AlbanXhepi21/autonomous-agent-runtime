import type { PublicRunEvent } from "@/types/analytics";

/**
 * Mirrors `InvestigationPlan` in `app/contracts/investigation.py`. This shape
 * travels inside `PublicRunEvent.data`, which is untyped JSON on the wire, so
 * it is read defensively here rather than trusted outright — the runtime
 * already reconciled every status against real evidence before it was sent;
 * this module only has to survive a malformed or unexpected payload.
 */
export interface InvestigationQuestion {
  id: string;
  question: string;
  status: "pending" | "answered" | "blocked";
  evidence_ids: string[];
}

export interface InvestigationOutput {
  id: string;
  kind: string;
  purpose: string;
  required: boolean;
  status: "pending" | "created" | "skipped" | "blocked";
  display_id: string | null;
}

export interface InvestigationPlan {
  objective: string;
  request_class: string;
  questions: InvestigationQuestion[];
  outputs: InvestigationOutput[];
  completion_criteria: string[];
  maximum_displays: number;
}

export interface InvestigationPlanProgress {
  questions_answered: number;
  questions_blocked: number;
  questions_total: number;
  outputs_created: number;
  outputs_blocked: number;
  outputs_required: number;
  outputs_total: number;
  maximum_displays: number;
}

function isQuestion(value: unknown): value is InvestigationQuestion {
  const question = value as Partial<InvestigationQuestion> | null;
  return (
    typeof question === "object" &&
    question !== null &&
    typeof question.id === "string" &&
    typeof question.question === "string" &&
    typeof question.status === "string" &&
    Array.isArray(question.evidence_ids)
  );
}

function isOutput(value: unknown): value is InvestigationOutput {
  const output = value as Partial<InvestigationOutput> | null;
  return (
    typeof output === "object" &&
    output !== null &&
    typeof output.id === "string" &&
    typeof output.kind === "string" &&
    typeof output.purpose === "string" &&
    typeof output.status === "string"
  );
}

function isPlan(value: unknown): value is InvestigationPlan {
  const plan = value as Partial<InvestigationPlan> | null;
  return (
    typeof plan === "object" &&
    plan !== null &&
    typeof plan.objective === "string" &&
    typeof plan.request_class === "string" &&
    Array.isArray(plan.questions) &&
    plan.questions.every(isQuestion) &&
    Array.isArray(plan.outputs) &&
    plan.outputs.every(isOutput)
  );
}

function isProgress(value: unknown): value is InvestigationPlanProgress {
  const progress = value as Partial<InvestigationPlanProgress> | null;
  return (
    typeof progress === "object" &&
    progress !== null &&
    typeof progress.questions_total === "number" &&
    typeof progress.outputs_total === "number" &&
    typeof progress.maximum_displays === "number"
  );
}

/** The most recent plan snapshot from a run's events, if the run ever planned one. */
export function latestPlanUpdate(
  events: PublicRunEvent[],
): { plan: InvestigationPlan; progress: InvestigationPlanProgress } | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.type !== "plan.updated") continue;
    const { plan, progress } = event.data;
    if (isPlan(plan) && isProgress(progress)) return { plan, progress };
  }
  return null;
}
