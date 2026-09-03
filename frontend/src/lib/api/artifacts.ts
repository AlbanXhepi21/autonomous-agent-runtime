import { eventUrl, request } from "@/lib/api/client";
import type { ArtifactMetadata } from "@/types/api";

export type { ArtifactMetadata as Artifact };

export const artifactsApi = {
  // Listing needs an explicit workspace_id query param -- there's no single
  // artifact ID here to resolve one from, unlike preview/downloadUrl below.
  list: (workspaceId: string, runId?: string) =>
    request<ArtifactMetadata[]>(
      `/artifacts?workspace_id=${encodeURIComponent(workspaceId)}${runId ? `&run_id=${encodeURIComponent(runId)}` : ""}`,
    ),
  // Deliberately no workspaceId parameter: this URL shape is embedded in
  // delivery emails/webhooks and must keep working for a recipient with no
  // other context. The backend resolves the owning workspace from the
  // artifact ID itself and verifies membership from there.
  preview: (id: string) =>
    request<{ content: string; truncated: boolean; media_type: string }>(`/artifacts/${id}/preview`),
  downloadUrl: (id: string) => eventUrl(`/artifacts/${id}`),
};
