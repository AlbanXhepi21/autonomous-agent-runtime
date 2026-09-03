"use client";

import { FormEvent, useEffect, useState } from "react";
import { useSettings } from "@/features/settings/settings-context";
import { analyticsApi } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";
import { workspacesApi } from "@/lib/api/workspaces";
import { canEditOrganization } from "@/lib/tenancy/permissions";
import type { NarrativePolicyDefault, ReportPreferences, ReportTemplate } from "@/types/api";

const NARRATIVE_OPTIONS: { value: NarrativePolicyDefault; label: string; description: string }[] = [
  {
    value: "exclude",
    label: "Exclude narrative",
    description: "Every execution is facts only, no written narrative.",
  },
  {
    value: "include_original",
    label: "Include original narrative",
    description:
      "Reuse the narrative captured when the report was defined, with a pinned-period notice.",
  },
  {
    value: "require_new_investigation",
    label: "Require a new investigation",
    description:
      "Refuse to auto-generate a narrative; only a fresh, explicitly requested analysis may write one.",
  },
];

export function ReportPreferencesSettings() {
  const { workspaceId, role } = useSettings();
  const [preferences, setPreferences] = useState<ReportPreferences | null>(null);
  const [templates, setTemplates] = useState<ReportTemplate[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([workspacesApi.getReportPreferences(workspaceId), analyticsApi.reportTemplates(workspaceId)])
      .then(([preferencesResult, templatesResult]) => {
        if (cancelled) return;
        setPreferences(preferencesResult);
        setTemplates(templatesResult.items);
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setLoadError(
            error instanceof ApiError ? error.message : "Report preferences could not be loaded.",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  if (loading) {
    return (
      <div className="settings-loading">
        <span className="spinner" />
        <p>Loading report preferences…</p>
      </div>
    );
  }
  if (loadError || !preferences || !templates || !role) {
    return (
      <div className="error" role="alert">
        {loadError ?? "Report preferences could not be loaded."}
      </div>
    );
  }

  return (
    <ReportPreferencesForm
      workspaceId={workspaceId}
      initial={preferences}
      templates={templates}
      editable={canEditOrganization(role)}
      onSaved={setPreferences}
    />
  );
}

function ReportPreferencesForm({
  workspaceId,
  initial,
  templates,
  editable,
  onSaved,
}: {
  workspaceId: string;
  initial: ReportPreferences;
  templates: ReportTemplate[];
  editable: boolean;
  onSaved: (preferences: ReportPreferences) => void;
}) {
  const [template, setTemplate] = useState(initial.default_template ?? "");
  const [format, setFormat] = useState(initial.default_output_format ?? "pdf");
  const [theme, setTheme] = useState(initial.default_theme ?? "");
  const [narrativePolicy, setNarrativePolicy] = useState<NarrativePolicyDefault>(
    initial.default_narrative_policy ?? "exclude",
  );
  const [evidenceAppendix, setEvidenceAppendix] = useState(initial.evidence_appendix_enabled);
  const [technicalAppendix, setTechnicalAppendix] = useState(
    initial.technical_sql_appendix_enabled,
  );
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      const updated = await workspacesApi.updateReportPreferences(workspaceId, {
        expected_version: initial.version,
        default_template: template || null,
        default_output_format: format,
        default_theme: theme || null,
        default_narrative_policy: narrativePolicy,
        evidence_appendix_enabled: evidenceAppendix,
        technical_sql_appendix_enabled: technicalAppendix,
      });
      onSaved(updated);
      setSaved(true);
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 409) {
        setError(
          "Someone else changed these preferences first. Reload the page to see the latest version.",
        );
      } else {
        setError(
          submitError instanceof ApiError
            ? submitError.message
            : "Report preferences could not be saved.",
        );
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Report preferences</h2>
        <p>
          {editable
            ? "Defaults used when a report is published without saying otherwise -- never a fact a report states."
            : "Read-only. Only an owner or admin can change report preferences."}
        </p>
      </div>
      <form className="settings-section" onSubmit={onSubmit}>
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
          <div className="field">
            <label htmlFor="report-template">Default template</label>
            <select
              id="report-template"
              value={template}
              onChange={(event) => setTemplate(event.target.value)}
              disabled={!editable}
            >
              <option value="">No default</option>
              {templates.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="report-format">Default format</label>
            <select
              id="report-format"
              value={format}
              onChange={(event) => setFormat(event.target.value as "pdf" | "docx")}
              disabled={!editable}
            >
              <option value="pdf">PDF</option>
              <option value="docx">Word (.docx)</option>
            </select>
          </div>
          <div className="field field-wide">
            <label htmlFor="report-theme">Theme</label>
            <input
              id="report-theme"
              type="text"
              value={theme}
              onChange={(event) => setTheme(event.target.value)}
              disabled={!editable}
              placeholder="No default"
            />
            <p className="field-hint">
              Stored for later use; it doesn&apos;t change how a report renders yet.
            </p>
          </div>
        </div>

        <h3>Narrative policy</h3>
        <div className="settings-grid">
          {NARRATIVE_OPTIONS.map((option) => (
            <label
              key={option.value}
              className="field field-wide"
              style={{ flexDirection: "row", alignItems: "flex-start", gap: 10 }}
            >
              <input
                type="radio"
                name="narrative-policy"
                value={option.value}
                checked={narrativePolicy === option.value}
                onChange={() => setNarrativePolicy(option.value)}
                disabled={!editable}
                style={{ marginTop: 3 }}
              />
              <span>
                <strong style={{ display: "block", fontSize: 13.5 }}>{option.label}</strong>
                <span className="field-hint" style={{ margin: 0 }}>
                  {option.description}
                </span>
              </span>
            </label>
          ))}
        </div>

        <h3>Appendices</h3>
        <div className="switch-row">
          <div className="settings-row-label">
            <strong>Evidence appendix</strong>
            <span>Include supporting query evidence by default when publishing.</span>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={evidenceAppendix}
              onChange={(event) => setEvidenceAppendix(event.target.checked)}
              disabled={!editable}
              aria-label="Evidence appendix enabled by default"
            />
            <span className="switch-track" />
          </label>
        </div>
        <div className="switch-row">
          <div className="settings-row-label">
            <strong>Technical SQL appendix</strong>
            <span>
              No current template prints a SQL appendix yet -- this preference has no visible
              effect.
            </span>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={technicalAppendix}
              onChange={(event) => setTechnicalAppendix(event.target.checked)}
              disabled={!editable}
              aria-label="Technical SQL appendix enabled by default"
            />
            <span className="switch-track" />
          </label>
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
