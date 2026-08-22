import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RunAnalysis } from "./run-analysis";

describe("RunAnalysis", () => {
  it("renders structured query, failure, and metric evidence without raw JSON", () => {
    render(
      <RunAnalysis
        run={{
          run_id: "r",
          status: "completed",
          created_at: "",
          started_at: "",
          completed_at: "",
          charts: [],
          error: null,
          metrics: {
            iterations: 3,
            tool_calls: 4,
            delegations: 0,
            total_duration_ms: 142,
            database_query_count: 2,
            database_rows_returned: 12,
            database_rejected_query_count: 0,
            total_tokens: 90,
            estimated_cost: 0.0012,
          },
        }}
        events={[
          {
            id: "q1",
            run_id: "r",
            type: "sql.query_completed",
            timestamp: "",
            data: {
              query_id: "query_003",
              duration_ms: 142,
              row_count: 12,
              referenced_tables: ["web_sessions", "web_events"],
            },
          },
          {
            id: "q2",
            run_id: "r",
            type: "sql.query_failed",
            timestamp: "",
            data: { query_id: "query_002", error: "column foo does not exist" },
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /view analysis/i }));
    expect(screen.getByText("Query #3 completed")).toBeInTheDocument();
    expect(screen.queryByText("Query #2 failed")).not.toBeInTheDocument();
    expect(screen.queryByText("Reason: column foo does not exist")).not.toBeInTheDocument();
    expect(screen.getByText("Tokens")).toBeInTheDocument();
    expect(screen.queryByText(/\{"query_id"/)).not.toBeInTheDocument();
  });
});
