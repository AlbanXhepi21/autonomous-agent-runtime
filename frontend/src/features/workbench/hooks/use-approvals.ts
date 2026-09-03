"use client";

import { useCallback, useState } from "react";
import { approvalsApi, type Approval } from "@/lib/api/approvals";

/**
 * The protected-action approval prompt.
 *
 * `resolve` reports the run the decision released so the caller can collect its
 * result, rather than taking a callback that would have to close over the run
 * hook this one is declared beside.
 */
export function useApprovals(workspaceId: string) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const [busy, setBusy] = useState(false);

  /** Load the approval a paused run is waiting on, if there is one. */
  const loadPending = useCallback(
    async (runId: string): Promise<Approval | null> => {
      const pending = (await approvalsApi.list(workspaceId, runId)).find((item) => item.status === "pending");
      setApproval(pending ?? null);
      return pending ?? null;
    },
    [workspaceId],
  );

  /** Returns the released run id, or null when the decision could not be recorded. */
  const resolve = useCallback(
    async (decision: "approve" | "reject"): Promise<string | null> => {
      if (!approval) return null;
      const runId = approval.run_id;
      setBusy(true);
      try {
        await (decision === "approve"
          ? approvalsApi.approve(workspaceId, approval.id)
          : approvalsApi.reject(workspaceId, approval.id));
        setApproval(null);
        return runId;
      } catch {
        return null;
      } finally {
        setBusy(false);
      }
    },
    [approval, workspaceId],
  );

  return { approval, setApproval, busy, loadPending, resolve };
}
