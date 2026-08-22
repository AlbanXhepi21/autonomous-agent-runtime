import { request } from "@/lib/api/client";
import type { WorkbenchConfig } from "@/types/api";

export const configApi = {
  get: () => request<WorkbenchConfig>("/api/v1/config"),
};
