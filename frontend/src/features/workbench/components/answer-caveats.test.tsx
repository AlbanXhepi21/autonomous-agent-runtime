import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnswerCaveats } from "@/features/workbench/components/answer-caveats";

const CAVEATS = [
  "Refund timing may differ from order timing.",
  "August 2026 is a partial month, so the total understates the period.",
];

describe("AnswerCaveats", () => {
  it("shows each limitation the analysis stated", () => {
    render(<AnswerCaveats caveats={CAVEATS} />);

    for (const caveat of CAVEATS) expect(screen.getByText(caveat)).toBeInTheDocument();
  });

  it("says nothing when the analysis stated no limitations", () => {
    const { container } = render(<AnswerCaveats caveats={[]} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("presents caveats read-only, with nothing to edit them through", () => {
    // A caveat qualifies the figures beside it, so changing its wording would
    // change what the report claims without changing the numbers it claims about.
    const { container } = render(<AnswerCaveats caveats={CAVEATS} />);

    expect(container.querySelectorAll("input, textarea, button, [contenteditable]")).toHaveLength(
      0,
    );
  });

  it("renders a caveat as text rather than as markup", () => {
    const hostile = "<script>alert(1)</script> Sample of 12 orders.";

    const { container } = render(<AnswerCaveats caveats={[hostile]} />);

    expect(screen.getByText(hostile)).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });
});
