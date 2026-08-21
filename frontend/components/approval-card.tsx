"use client";

import type { Approval } from "@/lib/api/approvals";

export function ApprovalCard({ approval, busy, onApprove, onReject }: { approval: Approval; busy: boolean; onApprove: () => void; onReject: () => void }) {
  return <section className="approval-card" aria-label="Approval required">
    <strong>Approval required</strong><p>{approval.reason}</p>
    <dl><dt>Agent</dt><dd>{approval.agent_name}</dd><dt>Action</dt><dd>{approval.tool_name}</dd><dt>Capability</dt><dd>{approval.capability}</dd>{approval.resource && <><dt>Resource</dt><dd>{approval.resource}</dd></>}</dl>
    <p className="muted">Only a safe summary is shown; executable arguments remain protected.</p>
    <div><button onClick={onApprove} disabled={busy}>Approve</button><button onClick={onReject} disabled={busy}>Reject</button></div>
  </section>;
}
