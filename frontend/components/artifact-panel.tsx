"use client";
import { useEffect, useMemo, useState } from "react";
import { SafeMarkdown } from "@/components/markdown";
import { explorerApi, type Artifact } from "@/lib/api/explorer";

export function ArtifactPanel({ runIds, refreshKey }: { runIds: string[]; refreshKey?: string }) {
  const [items, setItems] = useState<Artifact[]>([]);
  const [selected, setSelected] = useState<Artifact | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const runKey = useMemo(() => runIds.join(","), [runIds]);
  useEffect(() => {
    const ids = runKey ? runKey.split(",") : [];
    void Promise.all(ids.map((runId) => explorerApi.artifacts(runId)))
      .then((groups) => setItems(groups.flat()))
      .catch(() => setItems([]));
  }, [runKey, refreshKey]);
  const preview = async (artifact: Artifact) => {
    setSelected(artifact);
    if (!artifact.media_type.startsWith("image/"))
      setContent((await explorerApi.preview(artifact.artifact_id)).content);
  };
  return (
    <aside className="artifact-panel">
      <h2>Generated Outputs</h2>
      {items.length === 0 && <p>No generated outputs yet.</p>}
      <ul>
        {items.map((artifact) => (
          <li key={artifact.artifact_id}>
            <button onClick={() => void preview(artifact)}>{artifact.name}</button>
            <a href={explorerApi.downloadUrl(artifact.artifact_id)}>Download</a>
          </li>
        ))}
      </ul>
      {selected && (
        <section>
          <h3>{selected.name}</h3>
          {selected.media_type === "text/markdown" && content && <SafeMarkdown content={content} />}
          {selected.media_type === "text/csv" && content && <pre>{content}</pre>}
          {selected.media_type === "application/json" && content && <pre>{content}</pre>}
          {selected.media_type.startsWith("image/") && (
            // Artifacts are served by the API, not the Next image optimiser.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={explorerApi.downloadUrl(selected.artifact_id)} alt={selected.name} />
          )}
        </section>
      )}
    </aside>
  );
}
