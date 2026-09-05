"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { FormBanner, FormField } from "@/components/ui/form-field";
import { artifactsApi } from "@/lib/api/artifacts";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import { workspacesApi } from "@/lib/api/workspaces";
import type { UserSettings } from "@/types/api";

export function ProfileSettings({ uploadWorkspaceId }: { uploadWorkspaceId: string | null }) {
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
          setLoadError(error instanceof ApiError ? error.message : "Profile could not be loaded.");
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
        <p>Loading profile…</p>
      </div>
    );
  }
  if (loadError || !settings) {
    return (
      <div className="error" role="alert">
        {loadError ?? "Profile could not be loaded."}
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Profile</h2>
        <p>Your name and how the app is presented to you personally.</p>
      </div>
      <ProfileImageCard settings={settings} uploadWorkspaceId={uploadWorkspaceId} onChange={setSettings} />
      <ProfileDetailsCard settings={settings} onChange={setSettings} />
      <EmailChangeCard settings={settings} onChange={setSettings} />
    </div>
  );
}

function ProfileImageCard({
  settings,
  uploadWorkspaceId,
  onChange,
}: {
  settings: UserSettings;
  uploadWorkspaceId: string | null;
  onChange: (settings: UserSettings) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const onSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !uploadWorkspaceId) return;
    setError(null);
    setUploading(true);
    try {
      const updated = await workspacesApi.setProfileImage(uploadWorkspaceId, file);
      onChange(updated);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error ? uploadError.message : "The image could not be uploaded.",
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="settings-section">
      <h3>Profile image</h3>
      <div className="settings-row">
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {settings.profile_image_artifact_id ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={artifactsApi.downloadUrl(settings.profile_image_artifact_id)}
              alt=""
              width={56}
              height={56}
              style={{ borderRadius: "50%", objectFit: "cover", border: "1px solid var(--line)" }}
            />
          ) : (
            <div
              aria-hidden="true"
              style={{
                width: 56,
                height: 56,
                borderRadius: "50%",
                background: "var(--sidebar)",
                border: "1px solid var(--line)",
              }}
            />
          )}
          <div>
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => inputRef.current?.click()}
              disabled={uploading || !uploadWorkspaceId}
              title={uploadWorkspaceId ? undefined : "Join or create an organization first."}
            >
              {uploading ? "Uploading…" : "Change image"}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={onSelect}
              hidden
              disabled={!uploadWorkspaceId}
              aria-label="Upload profile image"
            />
          </div>
        </div>
      </div>
      {!uploadWorkspaceId ? (
        <p className="settings-section-desc" style={{ margin: "8px 0 0" }}>
          Join or create an organization to add a profile image.
        </p>
      ) : null}
      {error ? (
        <p className="form-banner error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function ProfileDetailsCard({
  settings,
  onChange,
}: {
  settings: UserSettings;
  onChange: (settings: UserSettings) => void;
}) {
  const [displayName, setDisplayName] = useState(settings.display_name);
  const [timezone, setTimezone] = useState(settings.preferred_timezone);
  const [locale, setLocale] = useState(settings.preferred_locale);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      const updated = await usersApi.updateSettings({
        display_name: displayName,
        preferred_timezone: timezone,
        preferred_locale: locale,
      });
      onChange(updated);
      setSaved(true);
    } catch (submitError) {
      setError(
        submitError instanceof ApiError ? submitError.message : "Profile could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="settings-section" onSubmit={onSubmit}>
      <h3>Details</h3>
      {saved ? (
        <p className="form-banner success" role="status">
          Saved.
        </p>
      ) : null}
      {error ? (
        <p className="form-banner error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="settings-grid">
        <div className="field field-wide">
          <label htmlFor="profile-display-name">Display name</label>
          <input
            id="profile-display-name"
            type="text"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
          />
        </div>
        <FormField
          id="profile-timezone"
          label="Preferred timezone"
          type="text"
          value={timezone}
          onChange={(event) => setTimezone(event.target.value)}
          hint="An IANA timezone, e.g. America/New_York."
          required
        />
        <FormField
          id="profile-locale"
          label="Preferred locale"
          type="text"
          value={locale}
          onChange={(event) => setLocale(event.target.value)}
          hint="A BCP-47 locale, e.g. en-US."
          required
        />
      </div>
      <div className="settings-actions">
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function EmailChangeCard({
  settings,
  onChange,
}: {
  settings: UserSettings;
  onChange: (settings: UserSettings) => void;
}) {
  const [open, setOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ newEmail?: string; currentPassword?: string }>(
    {},
  );
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const errors: typeof fieldErrors = {};
    if (!EMAIL_PATTERN.test(newEmail)) errors.newEmail = "Enter a valid email address.";
    if (!currentPassword) errors.currentPassword = "Enter your current password.";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await usersApi.requestEmailChange({ new_email: newEmail, current_password: currentPassword });
      setSent(true);
      const refreshed = await usersApi.getSettings();
      onChange(refreshed);
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.code === "invalid_credentials") {
        setFieldErrors({ currentPassword: submitError.message });
      } else if (
        submitError instanceof ApiError &&
        submitError.code === "email_already_registered"
      ) {
        setFieldErrors({ newEmail: submitError.message });
      } else {
        setError(
          submitError instanceof ApiError
            ? submitError.message
            : "This request could not be completed.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="settings-section">
      <h3>Email address</h3>
      <div className="settings-row">
        <div className="settings-row-label">
          <strong>{settings.email}</strong>
          {settings.pending_email ? (
            <span>Change to {settings.pending_email} pending confirmation.</span>
          ) : (
            <span>{settings.email_verified ? "Verified" : "Not verified"}</span>
          )}
        </div>
        {!open && !sent ? (
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={() => setOpen(true)}
          >
            Change email
          </button>
        ) : null}
      </div>
      {sent ? (
        <p className="form-banner success" role="status">
          Check {newEmail} for a link to confirm the change.
        </p>
      ) : open ? (
        <form onSubmit={onSubmit} className="settings-grid">
          {error ? (
            <p className="form-banner error field-wide" role="alert">
              {error}
            </p>
          ) : null}
          <FormField
            id="new-email"
            label="New email"
            type="email"
            value={newEmail}
            onChange={(event) => setNewEmail(event.target.value)}
            error={fieldErrors.newEmail}
            required
          />
          <FormField
            id="current-password-for-email"
            label="Current password"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            error={fieldErrors.currentPassword}
            required
          />
          <div className="settings-actions field-wide">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Sending…" : "Send confirmation"}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setOpen(false)}
              disabled={submitting}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
