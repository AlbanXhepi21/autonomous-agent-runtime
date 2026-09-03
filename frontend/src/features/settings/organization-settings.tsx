"use client";

import { FormEvent, useState } from "react";
import { FormField } from "@/components/ui/form-field";
import { useSettings } from "@/features/settings/settings-context";
import { ApiError } from "@/lib/api/client";
import { canEditOrganization } from "@/lib/tenancy/permissions";

export function OrganizationSettings() {
  const { workspace, role, updateWorkspace } = useSettings();
  // Safe to read `workspace`/`role` into initial state unconditionally: the
  // settings shell only renders its children once both have loaded (see
  // `SettingsBody` in settings-shell.tsx), so this component never mounts
  // with either still null.
  const [name, setName] = useState(workspace?.name ?? "");
  const [logoRef, setLogoRef] = useState(workspace?.logo_ref ?? "");
  const [timezone, setTimezone] = useState(workspace?.default_timezone ?? "");
  const [locale, setLocale] = useState(workspace?.default_locale ?? "");
  const [currency, setCurrency] = useState(workspace?.default_currency ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!workspace || !role) return null;

  const editable = canEditOrganization(role);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      await updateWorkspace({
        name,
        logo_ref: logoRef || null,
        default_timezone: timezone,
        default_locale: locale,
        default_currency: currency,
      });
      setSaved(true);
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 409) {
        setError(
          "Someone else changed these settings first. Reload the page to see the latest version.",
        );
      } else if (submitError instanceof ApiError && submitError.status === 422) {
        setError(submitError.message);
      } else {
        setError(
          submitError instanceof ApiError
            ? submitError.message
            : "Organization settings could not be saved.",
        );
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Organization</h2>
        <p>
          {editable
            ? "Identity and regional defaults for this organization."
            : "Read-only. Only an owner or admin can change organization settings."}
        </p>
      </div>
      <form className="settings-section" onSubmit={onSubmit}>
        <h3>Identity</h3>
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
            <label htmlFor="org-name">Organization name</label>
            <input
              id="org-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={!editable}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="org-slug">Slug</label>
            <input id="org-slug" type="text" value={workspace.slug} disabled readOnly />
            <p className="field-hint">The slug can&apos;t be changed after creation.</p>
          </div>
          <FormField
            id="org-logo"
            label="Logo"
            type="text"
            value={logoRef}
            onChange={(event) => setLogoRef(event.target.value)}
            disabled={!editable}
            hint="A URL or artifact reference for the organization's logo."
          />
        </div>
        <h3>Regional defaults</h3>
        <p className="settings-section-desc">
          These are formatting defaults only -- they change how future reports present figures,
          never the figures themselves. Already-published reports are not affected.
        </p>
        <div className="settings-grid">
          <FormField
            id="org-timezone"
            label="Timezone"
            type="text"
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
            disabled={!editable}
            hint="An IANA timezone, e.g. America/New_York."
            required
          />
          <FormField
            id="org-locale"
            label="Locale"
            type="text"
            value={locale}
            onChange={(event) => setLocale(event.target.value)}
            disabled={!editable}
            hint="A BCP-47 locale, e.g. en-US."
            required
          />
          <FormField
            id="org-currency"
            label="Currency"
            type="text"
            value={currency}
            onChange={(event) => setCurrency(event.target.value.toUpperCase())}
            disabled={!editable}
            hint="An ISO 4217 code, e.g. USD."
            maxLength={3}
            required
          />
        </div>
        {editable ? (
          <div className="settings-actions">
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        ) : null}
      </form>
    </div>
  );
}
