import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnswerSources } from "./answer-sources";
import type { AnswerSource } from "@/types/analytics";

const source: AnswerSource = {
  id: "query_003",
  kind: "database_query",
  run_id: "run-1",
  label: "Revenue by category",
  referenced_tables: ["orders", "order_items"],
  columns: [],
  metric: null,
  dimensions: [],
  filters: [],
  sql_fingerprint: null,
  row_count: 12,
  truncated: false,
  executed_at: "2026-08-22T13:31:00Z",
};

describe("AnswerSources", () => {
  it("names the evidence and what it read", () => {
    render(<AnswerSources sources={[source]} />);

    expect(screen.getByText("query_003")).toBeInTheDocument();
    expect(screen.getByText("Revenue by category")).toBeInTheDocument();
    expect(screen.getByTitle(/orders, order_items · 12 rows/)).toBeInTheDocument();
  });

  it("says what a citation does and does not establish", () => {
    render(<AnswerSources sources={[source]} />);

    expect(screen.getByText(/not a check that the figure came from it/)).toBeInTheDocument();
  });

  it("renders nothing when an answer cites no evidence", () => {
    const { container } = render(<AnswerSources sources={[]} />);

    expect(container).toBeEmptyDOMElement();
  });
});
