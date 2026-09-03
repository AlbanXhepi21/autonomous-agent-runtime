"use client";

import { useEffect, useState } from "react";
import { artifactsApi, type Artifact } from "@/lib/api/artifacts";
import { useWorkspaceId } from "@/features/workbench/workspace-context";

export function RunChartPreview({ runId }: { runId: string }) {
  const workspaceId = useWorkspaceId();
  const [chart, setChart] = useState<Artifact | null>(null);

  useEffect(() => {
    let active = true;
    void artifactsApi
      .list(workspaceId, runId)
      .then((items) => {
        if (active)
          setChart(
            items.find((item) => item.type === "chart" && item.media_type.startsWith("image/")) ??
              null,
          );
      })
      .catch(() => {
        if (active) setChart(null);
      });
    return () => {
      active = false;
    };
  }, [runId, workspaceId]);

  if (!chart) return null;
  return (
    <figure className="run-chart-preview">
      {/* eslint-disable-next-line @next/next/no-img-element -- charts are served
          by the API, not the Next image optimiser. */}
      <img src={artifactsApi.downloadUrl(chart.artifact_id)} alt={chart.name} />
      <figcaption>Generated chart: {chart.name}</figcaption>
    </figure>
  );
}
