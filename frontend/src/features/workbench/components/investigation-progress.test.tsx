import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InvestigationProgress } from "@/features/workbench/components/investigation-progress";
import type { PublicRunEvent } from "@/types/analytics";

function planEvent(): PublicRunEvent {
  return {
    id: "e1",
    run_id: "r1",
    type: "plan.updated",
    timestamp: "2026-01-01T00:00:00Z",
    data: {
      plan: {
        objective: "Analyze payment failures in 2026",
        request_class: "executive_report",
        questions: [],
        outputs: [],
        completion_criteria: [],
        maximum_displays: 6,
      },
      progress: {
        questions_answered: 2,
        questions_blocked: 1,
        questions_total: 3,
        outputs_created: 1,
        outputs_blocked: 0,
        outputs_required: 3,
        outputs_total: 4,
        maximum_displays: 6,
      },
    },
  };
}

describe("InvestigationProgress", () => {
  it("renders nothing while no plan has been created", () => {
    const { container } = render(<InvestigationProgress events={[]} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows the objective, request class, and counts from the latest plan snapshot", () => {
    render(<InvestigationProgress events={[planEvent()]} />);

    expect(screen.getByText("Analyze payment failures in 2026")).toBeInTheDocument();
    expect(screen.getByText("Executive report")).toBeInTheDocument();
    expect(screen.getByText("2/3 answered")).toBeInTheDocument();
    expect(screen.getByText("1/3 created")).toBeInTheDocument();
    expect(screen.getByText("1 / 6 budget")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("is read-only, with nothing to edit the plan through", () => {
    const { container } = render(<InvestigationProgress events={[planEvent()]} />);

    expect(container.querySelectorAll("input, textarea, button, [contenteditable]")).toHaveLength(0);
  });
});
