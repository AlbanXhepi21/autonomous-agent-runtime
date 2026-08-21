"use client";
import { useEffect, useRef, useState } from "react";
import { explorerApi, type DatabaseTable, type TableDescription } from "@/lib/api/explorer";

function isDatabaseTable(value: unknown): value is DatabaseTable {
  return Boolean(value && typeof value === "object" && typeof (value as DatabaseTable).name === "string" && (value as DatabaseTable).name.trim());
}

export function DatabaseExplorer() {
  const [tables, setTables] = useState<DatabaseTable[]>([]); const [selected, setSelected] = useState<TableDescription | null>(null); const [loading, setLoading] = useState<string | null>(null); const [query, setQuery] = useState(""); const [error, setError] = useState<string | null>(null);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => { void explorerApi.tables().then((result) => setTables(Array.isArray(result?.tables) ? result.tables.filter(isDatabaseTable) : [])).catch(() => setError("Database schema is unavailable.")); }, []);
  useEffect(() => { if (selected) panel.current?.scrollIntoView?.({ behavior: "smooth", block: "start" }); }, [selected]);
  const choose = async (name: string) => {
    if (selected?.name === name) { setSelected(null); return; }
    setLoading(name);
    try { setSelected(await explorerApi.table(name)); setError(null); }
    catch { setError("Table details are unavailable."); }
    finally { setLoading(null); }
  };
  const shown = tables.filter((table) => table.name.toLowerCase().includes(query.toLowerCase()));
  return <aside className="explorer-panel" ref={panel}>
    <h2>Database <small>{tables.length} tables</small></h2>
    <input aria-label="Search database schema" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search schema" />
    {error && <p>{error}</p>}
    <div className="schema-layout">
      <nav>{shown.map((table) => <button key={table.name} className={`schema-chip ${selected?.name === table.name ? "active" : ""} ${loading === table.name ? "loading" : ""}`} aria-pressed={selected?.name === table.name} onClick={() => void choose(table.name)}>{table.name}</button>)}</nav>
      {selected && <section className="table-detail">
        <header><h3>{selected.name}</h3><button className="table-detail-close" aria-label="Close table details" onClick={() => setSelected(null)}>×</button></header>
        <div className="table-detail-body">
          <h4>Columns <small>{selected.columns.length}</small></h4>
          <ul>{selected.columns.map((column) => <li key={column.name}><strong>{column.name}</strong> <span className="column-type">{column.data_type}</span>{column.primary_key && <span className="column-flag pk">PK</span>}{!column.nullable && <span className="column-flag">required</span>}</li>)}</ul>
          {selected.foreign_keys.length > 0 && <><h4>Relationships</h4><ul className="relationships">{selected.foreign_keys.map((key, index) => <li key={index}>{key.source_column} → {key.target_table}.{key.target_column}</li>)}</ul></>}
        </div>
      </section>}
    </div>
  </aside>;
}
