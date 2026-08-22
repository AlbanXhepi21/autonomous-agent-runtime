import { eventUrl, request } from "@/lib/api/client";
import type { ArtifactMetadata } from "@/types/api";

export type { ArtifactMetadata as Artifact };

export const artifactsApi = {
  list: (runId?: string) =>
    request<ArtifactMetadata[]>(`/artifacts${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`),
  preview: (id: string) =>
    request<{ content: string; truncated: boolean; media_type: string }>(
      `/artifacts/${id}/preview`,
    ),
  downloadUrl: (id: string) => eventUrl(`/artifacts/${id}`),
};
