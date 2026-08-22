"use client";
import { useEffect, useState } from "react";
import { request } from "@/lib/api/client";

type Memory = {
  id: string;
  type: "working" | "episodic" | "long_term";
  content: string;
  run_id: string | null;
  session_id: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};
const labels = { working: "Working", episodic: "Episodic", long_term: "Semantic / long-term" };

export function MemoryInspector() {
  const [items, setItems] = useState<Memory[]>([]);
  const [type, setType] = useState<Memory["type"] | "">("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void request<Memory[]>(`/api/v1/memory${type ? `?memory_type=${type}` : ""}`)
      .then(setItems)
      .catch(() => setError("Memory inspection is unavailable."));
  }, [type]);
  return (
    <aside className="memory-panel">
      <h2>Memory</h2>
      <p className="muted">
        Retained information for future reasoning—not chat history or run trace.
      </p>
      <select
        aria-label="Memory type"
        value={type}
        onChange={(event) => setType(event.target.value as typeof type)}
      >
        <option value="">All types</option>
        <option value="long_term">Semantic / long-term</option>
        <option value="episodic">Episodic</option>
        <option value="working">Working</option>
      </select>
      {error && <p>{error}</p>}
      {!error && items.length === 0 && <p className="muted">No retained memories.</p>}
      <ul>
        {items.map((memory) => (
          <li key={memory.id}>
            <strong>{labels[memory.type]}</strong>
            <time>{new Date(memory.created_at).toLocaleString()}</time>
            <p>{memory.content}</p>
            {memory.run_id && <small>Source run: {memory.run_id}</small>}
            {memory.session_id && <small>Session: {memory.session_id}</small>}
            {typeof memory.metadata.category === "string" && (
              <small>Category: {memory.metadata.category}</small>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}
