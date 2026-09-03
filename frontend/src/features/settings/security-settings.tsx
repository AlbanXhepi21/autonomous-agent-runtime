"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { FormField } from "@/components/ui/form-field";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import type { UserSettings } from "@/types/api";

export function SecuritySettings() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    usersApi
      .getSettings()
      .then((result) => {
        if (!cancelled) setSettings(result);
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setLoadError(
            error instanceof ApiError ? error.message : "Security settings could not be loaded.",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="settings-loading">
        <span className="spinner" />
        <p>Loading security settings…</p>
      </div>
    );
  }
  if (loadError || !settings) {
    return (
      <div className="error" role="alert">
        {loadError ?? "Security settings could not be loaded."}
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Security</h2>
        <p>Your password, sign-in sessions, and how your email address is verified.</p>
      </div>
      <ChangePasswordCard />
      <SessionsCard />
      <EmailVerificationCard settings={settings} />
      <MultiFactorCard />
    </div>
  );
}

function ChangePasswordCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    currentPassword?: string;
    newPassword?: string;
    confirmPassword?: string;
  }>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaved(false);
    const errors: typeof fieldErrors = {};
    if (!currentPassword) errors.currentPassword = "Enter your current password.";
    if (newPassword.length < 8) errors.newPassword = "Use at least 8 characters.";
    if (confirmPassword !== newPassword) errors.confirmPassword = "Passwords do not match.";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSaved(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.code === "invalid_credentials") {
        setFieldErrors({ currentPassword: submitError.message });
      } else if (submitError instanceof ApiError && submitError.code === "weak_password") {
        setFieldErrors({ newPassword: submitError.message });
      } else {
        setError(
          submitError instanceof ApiError ? submitError.message : "Password could not be changed.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="settings-section" onSubmit={onSubmit}>
      <h3>Password</h3>
      {saved ? (
        <p className="form-banner success" role="status">
          Password changed. Other sessions have been signed out.
        </p>
      ) : null}
      {error ? (
        <p className="form-banner error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="settings-grid">
        <FormField
          id="current-password"
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          error={fieldErrors.currentPassword}
          required
        />
        <div />
        <FormField
          id="new-password"
          label="New password"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          error={fieldErrors.newPassword}
          required
        />
        <FormField
          id="confirm-new-password"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={fieldErrors.confirmPassword}
          required
        />
      </div>
      <div className="settings-actions">
        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? "Changing…" : "Change password"}
        </button>
      </div>
    </form>
  );
}

function SessionsCard() {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signOutEverywhere = async () => {
    setBusy(true);
    setError(null);
    try {
      await authApi.logoutAll();
      router.push("/login");
    } catch (submitError) {
      setError(
        submitError instanceof ApiError
          ? submitError.message
          : "Could not sign out of every device.",
      );
      setBusy(false);
    }
  };

  return (
    <div className="settings-section">
      <h3>Sessions</h3>
      <p className="settings-section-desc">
        Viewing and revoking individual devices isn&apos;t available yet. You can sign out of every
        device at once, including this one.
      </p>
      <div className="settings-actions">
        <button type="button" className="btn btn-secondary" onClick={() => setConfirming(true)}>
          Sign out of all devices
        </button>
      </div>
      {confirming ? (
        <ConfirmDialog
          title="Sign out everywhere?"
          description="This immediately ends every session for your account, including this one -- you'll need to sign in again."
          confirmLabel="Sign out everywhere"
          busy={busy}
          error={error}
          onConfirm={signOutEverywhere}
          onCancel={() => {
            setConfirming(false);
            setError(null);
          }}
        />
      ) : null}
    </div>
  );
}

function EmailVerificationCard({ settings }: { settings: UserSettings }) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resend = async () => {
    setSending(true);
    setError(null);
    try {
      await authApi.resendVerification();
      setSent(true);
    } catch (submitError) {
      setError(
        submitError instanceof ApiError
          ? submitError.message
          : "Verification email could not be sent.",
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="settings-section">
      <h3>Email verification</h3>
      <div className="settings-row">
        <div className="settings-row-label">
          <strong>{settings.email}</strong>
          <span>
            <span
              className={
                settings.email_verified ? "badge badge-verified" : "badge badge-unverified"
              }
            >
              {settings.email_verified ? "Verified" : "Not verified"}
            </span>
          </span>
        </div>
        {!settings.email_verified ? (
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={resend}
            disabled={sending || sent}
          >
            {sent ? "Sent" : sending ? "Sending…" : "Resend verification email"}
          </button>
        ) : null}
      </div>
      {error ? (
        <p className="form-banner error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function MultiFactorCard() {
  return (
    <div className="settings-section">
      <h3>Two-factor authentication</h3>
      <div className="settings-row">
        <div className="settings-row-label">
          <strong>Not available yet</strong>
          <span>Two-factor authentication is coming later.</span>
        </div>
        <button type="button" className="btn btn-secondary btn-small" disabled>
          Set up
        </button>
      </div>
    </div>
  );
}
