import type { ReactNode } from "react";

export function TenantStateCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="tenant-state-shell">
      <div className="tenant-state-card">
        <h1>{title}</h1>
        {children}
      </div>
    </div>
  );
}
