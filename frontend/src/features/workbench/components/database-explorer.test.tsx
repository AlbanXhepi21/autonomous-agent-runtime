import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DatabaseExplorer } from "./database-explorer";
import { schemaApi } from "@/lib/api/schema";

vi.mock("@/lib/api/schema", () => ({ schemaApi: { tables: vi.fn(), table: vi.fn() } }));

describe("DatabaseExplorer", () => {
  it("ignores malformed table entries and renders the backend table-detail contract", async () => {
    vi.mocked(schemaApi.tables).mockResolvedValue({
      schemas: ["public"],
      tables: [undefined, { name: "orders", schema: "public" }] as never[],
    });
    vi.mocked(schemaApi.table).mockResolvedValue({
      name: "orders",
      schema: "public",
      primary_key: ["id"],
      unique_constraints: [],
      columns: [
        {
          name: "id",
          data_type: "uuid",
          nullable: false,
          primary_key: true,
          foreign_key_target: null,
        },
      ],
      foreign_keys: [
        {
          source_table: "orders",
          source_schema: "public",
          source_column: "customer_id",
          target_table: "customers",
          target_schema: "public",
          target_column: "id",
        },
      ],
    });
    render(<DatabaseExplorer />);
    expect(await screen.findByRole("button", { name: "orders" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "orders" }));
    expect(await screen.findByText("customer_id → customers.id")).toBeInTheDocument();
  });
});
