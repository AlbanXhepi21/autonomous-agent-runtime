"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useSettings } from "@/features/settings/settings-context";
import { ApiError } from "@/lib/api/client";
import { workspacesApi } from "@/lib/api/workspaces";
import { canDeactivateOrganization, canTransferOwnership } from "@/lib/tenancy/permissions";
import { forgetLastWorkspaceId } from "@/lib/auth/last-workspace";

export function DangerZone() {
  const { workspace, members, role, currentUserId } = useSettings();

  if (!workspace || !members || !role) return null;

  const activeOwners = members.filter(
    (member) => member.role === "owner" && member.status === "active",
  );
  const isOnlyOwner =
    role === "owner" && activeOwners.length === 1 && activeOwners[0].user_id === currentUserId;

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Danger zone</h2>
        <p>These actions are hard to undo. Read each one carefully before continuing.</p>
      </div>

      <LeaveCard workspaceName={workspace.name} isOnlyOwner={isOnlyOwner} />

      {canTransferOwnership(role) ? (
        <TransferOwnershipCard
          workspaceId={workspace.id}
          members={members}
          currentUserId={currentUserId}
        />
      ) : null}

      {canDeactivateOrganization(role) ? (
        <DeactivateCard workspaceId={workspace.id} workspaceName={workspace.name} />
      ) : null}
    </div>
  );
}

function LeaveCard({
  workspaceName,
  isOnlyOwner,
}: {
  workspaceName: string;
  isOnlyOwner: boolean;
}) {
  const router = useRouter();
  const { workspaceId } = useSettings();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const leave = async () => {
    setBusy(true);
    setError(null);
    try {
      await workspacesApi.leave(workspaceId);
      forgetLastWorkspaceId();
      router.push("/");
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.code === "last_owner") {
        setError("You're the only owner -- transfer ownership before leaving.");
      } else {
        setError(
          submitError instanceof ApiError
            ? submitError.message
            : "You could not be removed from this organization.",
        );
      }
      setBusy(false);
    }
  };

  return (
    <div className="danger-card">
      <h3>Leave organization</h3>
      <div className="danger-card-row">
        <p>
          You&apos;ll immediately lose access to {workspaceName}. Someone with access will need to
          invite you again.
        </p>
        <button
          type="button"
          className="btn btn-danger"
          onClick={() => setConfirming(true)}
          disabled={isOnlyOwner}
        >
          Leave organization
        </button>
      </div>
      {isOnlyOwner ? (
        <p className="last-owner-notice">
          You&apos;re the only owner of this organization. Transfer ownership to someone else before
          you can leave.
        </p>
      ) : null}
      {confirming ? (
        <ConfirmDialog
          title="Leave this organization?"
          description={`You'll lose access to ${workspaceName} right away.`}
          confirmLabel="Leave organization"
          busy={busy}
          error={error}
          onConfirm={leave}
          onCancel={() => {
            setConfirming(false);
            setError(null);
          }}
        />
      ) : null}
    </div>
  );
}

function TransferOwnershipCard({
  workspaceId,
  members,
  currentUserId,
}: {
  workspaceId: string;
  members: { user_id: string; role: string; status: string }[];
  currentUserId: string;
}) {
  const candidates = members.filter(
    (member) => member.user_id !== currentUserId && member.status === "active",
  );
  const [target, setTarget] = useState(candidates[0]?.user_id ?? "");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const transfer = async () => {
    setBusy(true);
    setError(null);
    try {
      await workspacesApi.transferOwnership(workspaceId, { to_user_id: target });
      setDone(true);
      setConfirming(false);
    } catch (submitError) {
      setError(
        submitError instanceof ApiError
          ? submitError.message
          : "Ownership could not be transferred.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="danger-card">
      <h3>Transfer ownership</h3>
      <p style={{ margin: 0, color: "var(--muted)", fontSize: 12.5, lineHeight: 1.5 }}>
        Makes another active member the owner. You keep your membership at your current role.
      </p>
      {done ? (
        <p className="form-banner success" role="status">
          Ownership transferred.
        </p>
      ) : candidates.length === 0 ? (
        <p className="muted">There&apos;s no other active member to transfer ownership to.</p>
      ) : (
        <div className="danger-card-row">
          <div className="field" style={{ minWidth: 220 }}>
            <label htmlFor="transfer-target">New owner</label>
            <select
              id="transfer-target"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
            >
              {candidates.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  Member {member.user_id.slice(0, 8)} ({member.role})
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="btn btn-danger" onClick={() => setConfirming(true)}>
            Transfer ownership
          </button>
        </div>
      )}
      {confirming ? (
        <ConfirmDialog
          title="Transfer ownership?"
          description="The selected member becomes the organization's owner immediately. This cannot be undone from here -- they would need to transfer it back."
          confirmLabel="Transfer ownership"
          busy={busy}
          error={error}
          onConfirm={transfer}
          onCancel={() => {
            setConfirming(false);
            setError(null);
          }}
        />
      ) : null}
    </div>
  );
}

function DeactivateCard({
  workspaceId,
  workspaceName,
}: {
  workspaceId: string;
  workspaceName: string;
}) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deactivate = async () => {
    setBusy(true);
    setError(null);
    try {
      await workspacesApi.deactivate(workspaceId);
      forgetLastWorkspaceId();
      router.push("/");
    } catch (submitError) {
      setError(
        submitError instanceof ApiError
          ? submitError.message
          : "This organization could not be deactivated.",
      );
      setBusy(false);
    }
  };

  return (
    <div className="danger-card">
      <h3>Deactivate organization</h3>
      <div className="danger-card-row">
        <p>
          {workspaceName} becomes inaccessible to every member, including you. This does not delete
          any data and can only be reversed by contacting support.
        </p>
        <button type="button" className="btn btn-danger" onClick={() => setConfirming(true)}>
          Deactivate organization
        </button>
      </div>
      {confirming ? (
        <ConfirmDialog
          title="Deactivate this organization?"
          description="Every member, including you, immediately loses access."
          confirmText={workspaceName}
          confirmLabel="Deactivate organization"
          busy={busy}
          error={error}
          onConfirm={deactivate}
          onCancel={() => {
            setConfirming(false);
            setError(null);
          }}
        />
      ) : null}
    </div>
  );
}
