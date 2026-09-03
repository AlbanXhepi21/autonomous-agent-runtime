"use client";

import { FormEvent, useState } from "react";
import { FormField } from "@/components/ui/form-field";
import { useSettings } from "@/features/settings/settings-context";
import { ApiError } from "@/lib/api/client";
import { canEditOrganization } from "@/lib/tenancy/permissions";

const NUMBER_FORMATS = ["1,234.56", "1.234,56", "1 234,56", "1'234.56"];
const DATE_FORMATS = ["YYYY-MM-DD", "MM/DD/YYYY", "DD/MM/YYYY", "DD.MM.YYYY"];
const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function RegionalSettings() {
  const { workspace, role, updateWorkspace } = useSettings();

  const [timezone, setTimezone] = useState(workspace?.default_timezone ?? "");
  const [locale, setLocale] = useState(workspace?.default_locale ?? "");
  const [currency, setCurrency] = useState(workspace?.default_currency ?? "");
  const [numberFormat, setNumberFormat] = useState(workspace?.number_format ?? NUMBER_FORMATS[0]);
  const [dateFormat, setDateFormat] = useState(workspace?.date_format ?? DATE_FORMATS[0]);
  const [fiscalMonth, setFiscalMonth] = useState(workspace?.fiscal_year_start_month ?? 1);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!workspace || !role) return null;

  const editable = canEditOrganization(role);
  const numberFormatOptions = NUMBER_FORMATS.includes(numberFormat)
    ? NUMBER_FORMATS
    : [numberFormat, ...NUMBER_FORMATS];
  const dateFormatOptions = DATE_FORMATS.includes(dateFormat)
    ? DATE_FORMATS
    : [dateFormat, ...DATE_FORMATS];

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      await updateWorkspace({
        default_timezone: timezone,
        default_locale: locale,
        default_currency: currency,
        number_format: numberFormat,
        date_format: dateFormat,
        fiscal_year_start_month: fiscalMonth,
      });
      setSaved(true);
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 409) {
        setError(
          "Someone else changed these settings first. Reload the page to see the latest version.",
        );
      } else {
        setError(
          submitError instanceof ApiError
            ? submitError.message
            : "Regional settings could not be saved.",
        );
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Regional &amp; data settings</h2>
        <p>
          {editable
            ? "How dates, numbers, and periods are presented across this organization."
            : "Read-only. Only an owner or admin can change regional settings."}
        </p>
      </div>
      <form className="settings-section" onSubmit={onSubmit}>
        <h3>Locale &amp; currency</h3>
        <p className="settings-section-desc">
          Presentation only -- changing these never rewrites a value already stated in a published
          report.
        </p>
        <div className="settings-grid">
          <FormField
            id="regional-timezone"
            label="Timezone"
            type="text"
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
            disabled={!editable}
            hint="An IANA timezone, e.g. America/New_York."
            required
          />
          <FormField
            id="regional-locale"
            label="Locale"
            type="text"
            value={locale}
            onChange={(event) => setLocale(event.target.value)}
            disabled={!editable}
            hint="A BCP-47 locale, e.g. en-US."
            required
          />
          <FormField
            id="regional-currency"
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

        <h3>Formatting</h3>
        <div className="settings-grid">
          <div className="field">
            <label htmlFor="regional-number-format">Number format</label>
            <select
              id="regional-number-format"
              value={numberFormat}
              onChange={(event) => setNumberFormat(event.target.value)}
              disabled={!editable}
            >
              {numberFormatOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="regional-date-format">Date format</label>
            <select
              id="regional-date-format"
              value={dateFormat}
              onChange={(event) => setDateFormat(event.target.value)}
              disabled={!editable}
            >
              {dateFormatOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="regional-fiscal-month">Fiscal year starts</label>
            <select
              id="regional-fiscal-month"
              value={fiscalMonth}
              onChange={(event) => setFiscalMonth(Number(event.target.value))}
              disabled={!editable}
            >
              {MONTHS.map((month, index) => (
                <option key={month} value={index + 1}>
                  {month}
                </option>
              ))}
            </select>
          </div>
        </div>

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
        {editable ? (
          <div className="settings-actions">
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        ) : null}
      </form>

      <div className="settings-section">
        <h3>Default report period</h3>
        <p className="settings-section-desc">
          There isn&apos;t an organization-wide default period today. Each saved report defines its
          own period (for example, &quot;previous month&quot; or a fixed date range) when it&apos;s
          created, from the Saved Reports panel in the workbench.
        </p>
      </div>
    </div>
  );
}
