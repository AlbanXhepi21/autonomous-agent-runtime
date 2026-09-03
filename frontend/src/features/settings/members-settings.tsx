"use client";

import { FormEvent, useState } from "react";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { FormField } from "@/components/ui/form-field";
import { useSettings } from "@/features/settings/settings-context";
import { ApiError } from "@/lib/api/client";
import { membershipsApi } from "@/lib/api/workspaces";
import {
  ASSIGNABLE_ROLES,
  ROLE_LABELS,
  canInviteRole,
  canManageMember,
  canManageMembers,
} from "@/lib/tenancy/permissions";
import type { Membership, Role } from "@/types/api";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Memberships carry only a `user_id` -- there's no API to resolve another
 * member's name or email today, so anyone but the caller is shown by a
 * short id. See the page-level notice. */
function memberLabel(
  member: Membership,
  currentUserId: string,
  currentUserDisplayName: string,
): string {
  if (member.user_id === currentUserId) return `${currentUserDisplayName} (you)`;
  return `Member ${member.user_id.slice(0, 8)}`;
}

export function MembersSettings() {
  const { workspaceId, members, role, currentUserId, currentUserDisplayName, refreshMembers } =
    useSettings();
  const [inviting, setInviting] = useState(false);

  if (!members || !role) return null;

  const canManage = canManageMembers(role);

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Members</h2>
        <p>
          {canManage
            ? "Who has access to this organization, and at what role."
            : "Read-only. Only an owner or admin can invite or manage members."}
        </p>
      </div>

      <div className="settings-section">
        <p className="settings-section-desc" style={{ margin: 0 }}>
          Member names and email addresses aren&apos;t available from the API for anyone but you yet
          -- other members are shown by a short id.
        </p>
      </div>

      {canManage ? (
        <div className="settings-section">
          <div className="settings-row">
            <h3 style={{ margin: 0 }}>Invite a member</h3>
            <button
              type="button"
              className="btn btn-primary btn-small"
              onClick={() => setInviting(true)}
            >
              Invite member
            </button>
          </div>
        </div>
      ) : null}

      <div className="members-table-wrap">
        <table className="members-table">
          <thead>
            <tr>
              <th>Member</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined</th>
              {canManage ? <th>Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <MemberRow
                key={member.id}
                member={member}
                workspaceId={workspaceId}
                actingRole={role}
                currentUserId={currentUserId}
                currentUserDisplayName={currentUserDisplayName}
                canManage={canManage}
                onChanged={refreshMembers}
              />
            ))}
          </tbody>
        </table>
      </div>

      {inviting ? (
        <InviteMemberDialog
          workspaceId={workspaceId}
          actingRole={role}
          onClose={() => setInviting(false)}
          onInvited={refreshMembers}
        />
      ) : null}
    </div>
  );
}

function MemberRow({
  member,
  workspaceId,
  actingRole,
  currentUserId,
  currentUserDisplayName,
  canManage,
  onChanged,
}: {
  member: Membership;
  workspaceId: string;
  actingRole: Role;
  currentUserId: string;
  currentUserDisplayName: string;
  canManage: boolean;
  onChanged: () => Promise<void>;
}) {
  const [changingRole, setChangingRole] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const manageable = canManageMember(actingRole, member.role);
  const isSelf = member.user_id === currentUserId;

  const changeRole = async (newRole: Role) => {
    setBusy(true);
    setError(null);
    try {
      await membershipsApi.changeRole(workspaceId, member.user_id, { role: newRole });
      await onChanged();
    } catch (submitError) {
      setError(
        submitError instanceof ApiError ? submitError.message : "The role could not be changed.",
      );
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      await membershipsApi.remove(workspaceId, member.user_id);
      await onChanged();
      setRemoving(false);
    } catch (submitError) {
      setError(
        submitError instanceof ApiError ? submitError.message : "This member could not be removed.",
      );
      setBusy(false);
    }
  };

  return (
    <>
      <tr>
        <td title={member.user_id}>{memberLabel(member, currentUserId, currentUserDisplayName)}</td>
        <td>
          <span className={`badge badge-role-${member.role}`}>{ROLE_LABELS[member.role]}</span>
        </td>
        <td>
          <span
            className={
              member.status === "active"
                ? "badge badge-status-active"
                : "badge badge-status-disabled"
            }
          >
            {member.status === "active" ? "Active" : "Disabled"}
          </span>
        </td>
        <td>{formatDate(member.joined_at ?? member.created_at)}</td>
        {canManage ? (
          <td>
            <div className="members-actions">
              {manageable && !isSelf ? (
                <>
                  {changingRole ? (
                    <select
                      autoFocus
                      defaultValue={member.role}
                      disabled={busy}
                      onChange={(event) => {
                        setChangingRole(false);
                        void changeRole(event.target.value as Role);
                      }}
                      onBlur={() => setChangingRole(false)}
                    >
                      {ASSIGNABLE_ROLES.map((option) => (
                        <option key={option} value={option}>
                          {ROLE_LABELS[option]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-secondary btn-small"
                      onClick={() => setChangingRole(true)}
                    >
                      Change role
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-danger btn-small"
                    onClick={() => setRemoving(true)}
                  >
                    Remove
                  </button>
                </>
              ) : (
                <span className="muted">{isSelf ? "That's you" : "Owner-only"}</span>
              )}
            </div>
            {error ? (
              <p className="field-error" role="alert">
                {error}
              </p>
            ) : null}
          </td>
        ) : null}
      </tr>
      {removing ? (
        <ConfirmDialog
          title="Remove this member?"
          description="They will immediately lose access to this organization. This can be undone by inviting them again."
          confirmLabel="Remove member"
          busy={busy}
          error={error}
          onConfirm={remove}
          onCancel={() => {
            setRemoving(false);
            setError(null);
          }}
        />
      ) : null}
    </>
  );
}

function InviteMemberDialog({
  workspaceId,
  actingRole,
  onClose,
  onInvited,
}: {
  workspaceId: string;
  actingRole: Role;
  onClose: () => void;
  onInvited: () => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const invitableRoles = ASSIGNABLE_ROLES.filter((candidate) =>
    canInviteRole(actingRole, candidate),
  );

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setFieldError(undefined);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setFieldError("Enter a valid email address.");
      return;
    }
    setSubmitting(true);
    try {
      await membershipsApi.invite(workspaceId, { email, role });
      setSent(true);
      await onInvited();
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.code === "duplicate_invitation") {
        setFieldError(submitError.message);
      } else {
        setError(
          submitError instanceof ApiError
            ? submitError.message
            : "This invitation could not be sent.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Invite a member"
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Invite a member</h2>
        {sent ? (
          <>
            <p className="form-banner success" role="status">
              Invitation sent to {email}.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" onClick={onClose}>
                Done
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            {error ? (
              <p className="form-banner error" role="alert">
                {error}
              </p>
            ) : null}
            <FormField
              id="invite-email"
              label="Email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              error={fieldError}
              required
            />
            <div className="field">
              <label htmlFor="invite-role">Role</label>
              <select
                id="invite-role"
                value={role}
                onChange={(event) => setRole(event.target.value as Role)}
              >
                {invitableRoles.map((option) => (
                  <option key={option} value={option}>
                    {ROLE_LABELS[option]}
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Sending…" : "Send invitation"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
