import { request } from "@/lib/api/client";
import type { DatabaseSchemaSummary, DatabaseTable, TableDescription } from "@/types/api";

export type { DatabaseTable, TableDescription };

export const schemaApi = {
  tables: () => request<DatabaseSchemaSummary>("/api/v1/schema/tables"),
  search: (query: string) =>
    request<DatabaseTable[]>(`/api/v1/schema/search?q=${encodeURIComponent(query)}`),
  table: (name: string) =>
    request<TableDescription>(`/api/v1/schema/tables/${encodeURIComponent(name)}`),
};
