"use client";

import { useEffect, useState } from "react";
import { explorerApi, type Artifact } from "@/lib/api/explorer";

export function RunChartPreview({ runId }: { runId: string }) {
  const [chart, setChart] = useState<Artifact | null>(null);

  useEffect(() => {
    let active = true;
    void explorerApi.artifacts(runId)
      .then((items) => { if (active) setChart(items.find((item) => item.type === "chart" && item.media_type.startsWith("image/")) ?? null); })
      .catch(() => { if (active) setChart(null); });
    return () => { active = false; };
  }, [runId]);

  if (!chart) return null;
  return <figure className="run-chart-preview"><img src={explorerApi.downloadUrl(chart.artifact_id)} alt={chart.name} /* eslint-disable-line @next/next/no-img-element */ /><figcaption>Generated chart: {chart.name}</figcaption></figure>;
}
