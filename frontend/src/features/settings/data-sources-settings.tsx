"use client";

import { FormEvent, useEffect, useState } from "react";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { FormField } from "@/components/ui/form-field";
import { useSettings } from "@/features/settings/settings-context";
import { ApiError } from "@/lib/api/client";
import { dataSourcesApi } from "@/lib/api/datasources";
import { canDeleteDataSources, canManageDataSources } from "@/lib/tenancy/permissions";
import type {
  ConnectionTestResult,
  DataSource,
  DataSourceCreateRequest,
  DataSourceEnvironment,
  DataSourceSslMode,
} from "@/types/api";

// -- safe defaults, mirroring the backend's own Pydantic field defaults ----
// (app/api/schemas/datasources.py::DataSourceCreateRequest /
// app/datasources/contracts.py::DataSourceConnectionConfig) -- never invent
// different numbers here.

const DEFAULT_PORT = 5432;
const DEFAULT_SSL_MODE: DataSourceSslMode = "require";
const DEFAULT_ENVIRONMENT: DataSourceEnvironment = "development";
const DEFAULT_STATEMENT_TIMEOUT_SECONDS = 15;
const DEFAULT_CONNECTION_TIMEOUT_SECONDS = 10;
const DEFAULT_MAX_RESULT_ROWS = 5_000;
const DEFAULT_MAX_RESULT_BYTES = 1_000_000;

const SSL_MODES: DataSourceSslMode[] = ["require", "verify-ca", "verify-full"];
const ENVIRONMENTS: DataSourceEnvironment[] = ["development", "staging", "production"];

export const ENVIRONMENT_LABELS: Record<DataSourceEnvironment, string> = {
  development: "Development",
  staging: "Staging",
  production: "Production",
};

// -- status/badge mapping ----------------------------------------------------
//
// The backend's connection-lifecycle status vocabulary (pending, testing,
// verified_read_only, active, failed, disabled, deleted -- see
// app.datasources.contracts.DataSourceStatus) doesn't map one-to-one onto
// the badge vocabulary this settings page shows. The mapping below is a
// deliberate simplification for the connection owner, not a renaming:
//
//   pending              -> "Draft"            -- created, nothing proven yet
//   testing               -> "Requires review"  -- connectivity confirmed,
//                                                  read-only check still owed
//   verified_read_only    -> "Requires review"  -- read-only confirmed, still
//                                                  needs a catalog table
//                                                  approved and activated
//   active                -> "Connected"
//   failed (auth category) -> "Authentication failed"
//   failed (other)         -> "Unreachable"
//   disabled               -> "Disabled"
//   deleted                -> "Deleted" (defensive only -- the list endpoint
//                                        never actually returns one)

export type StatusBadge = { label: string; className: string };

export function describeStatus(status: string, lastErrorCategory: string | null): StatusBadge {
  switch (status) {
    case "active":
      return { label: "Connected", className: "badge-ds-connected" };
    case "pending":
      return { label: "Draft", className: "badge-ds-draft" };
    case "testing":
    case "verified_read_only":
      return { label: "Requires review", className: "badge-ds-review" };
    case "disabled":
      return { label: "Disabled", className: "badge-ds-disabled" };
    case "failed":
      return lastErrorCategory === "authentication_failed"
        ? { label: "Authentication failed", className: "badge-ds-error" }
        : { label: "Unreachable", className: "badge-ds-error" };
    case "deleted":
      return { label: "Deleted", className: "badge-ds-disabled" };
    default:
      return { label: status, className: "badge-ds-draft" };
  }
}

/**
 * The backend never returns a live "is this actually read-only right now"
 * flag on the connection record -- only the connection-lifecycle status,
 * which the backend itself only advances past `verified_read_only`/`active`
 * once a real `verify-read-only` probe passed (see
 * `DataSourceOnboardingService.verify_read_only_behavior`/`activate`). This
 * reads that already-proven fact off the status rather than calling
 * verify-read-only again just to render a list row.
 */
export function readOnlyLabel(status: string): string {
  if (status === "verified_read_only" || status === "active") return "Read-only verified";
  if (status === "pending" || status === "testing") return "Not yet verified";
  return "Unknown";
}

/** Reduces a host to a shape safe to leave on screen by default -- not a
 * secret (the API already returns it in full), just resistant to a casual
 * screenshot or shared screen. */
export function maskHost(host: string): string {
  if (host.length <= 4) return "•".repeat(host.length);
  const visibleStart = host.slice(0, 2);
  const visibleEnd = host.slice(-4);
  const maskedLength = Math.max(3, host.length - visibleStart.length - visibleEnd.length);
  return `${visibleStart}${"•".repeat(maskedLength)}${visibleEnd}`;
}

function formatDateTime(value: string | null): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

// -- top-level page -----------------------------------------------------------

export function DataSourcesSettings() {
  const { workspaceId, role } = useSettings();
  if (!role) return null;
  // Keying on workspaceId forces a full remount on every organization
  // switch: in-flight fetches from the old workspace can never land in this
  // component's state, any open add/edit/replace-credentials/disable/delete
  // dialog for the old tenant is torn down instead of lingering, and the
  // list always starts back at "loading" rather than briefly showing the
  // previous organization's connections while the new fetch is in flight.
  return <DataSourcesSettingsPanel key={workspaceId} workspaceId={workspaceId} role={role} />;
}

function DataSourcesSettingsPanel({
  workspaceId,
  role,
}: {
  workspaceId: string;
  role: NonNullable<ReturnType<typeof useSettings>["role"]>;
}) {
  const [items, setItems] = useState<DataSource[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<DataSource | null>(null);
  const [replacingCredentials, setReplacingCredentials] = useState<DataSource | null>(null);
  const [testing, setTesting] = useState<DataSource | null>(null);
  const [disabling, setDisabling] = useState<DataSource | null>(null);
  const [enabling, setEnabling] = useState<DataSource | null>(null);
  const [deleting, setDeleting] = useState<DataSource | null>(null);

  const load = async () => {
    const result = await dataSourcesApi.list(workspaceId);
    setItems(result.items);
  };

  useEffect(() => {
    // This component is remounted (via `key={workspaceId}` in
    // DataSourcesSettings) on every organization switch, so this effect only
    // ever runs once per mount -- the initial `loading`/`loadError` state
    // already covers a fresh fetch without needing to reset them here.
    let cancelled = false;
    dataSourcesApi
      .list(workspaceId)
      .then((result) => {
        if (cancelled) return;
        setItems(result.items);
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(errorMessage(error, "Data sources could not be loaded."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  const refresh = async () => {
    try {
      await load();
    } catch (error) {
      setLoadError(errorMessage(error, "Data sources could not be refreshed."));
    }
  };

  const canManage = canManageDataSources(role);
  const canDelete = canDeleteDataSources(role);

  return (
    <div className="settings-page" style={{ maxWidth: 980 }}>
      <div className="settings-page-header">
        <h2>Data sources</h2>
        <p>
          {canManage
            ? "PostgreSQL connections this organization's analyses can read from. Every connection is read-only by design."
            : "Read-only. Only an owner or admin can add or manage data sources."}
        </p>
      </div>

      {canManage ? (
        <div className="settings-section">
          <div className="settings-row">
            <h3 style={{ margin: 0 }}>Connections</h3>
            <button type="button" className="btn btn-primary btn-small" onClick={() => setAdding(true)}>
              Add connection
            </button>
          </div>
        </div>
      ) : null}

      {loading ? (
        <DataSourcesSkeleton />
      ) : loadError ? (
        <div className="error" role="alert">
          {loadError}
        </div>
      ) : !items || items.length === 0 ? (
        <div className="empty-state">
          <h3>No data sources connected</h3>
          <p>Add a read-only PostgreSQL database to begin analyzing your organization&apos;s data.</p>
        </div>
      ) : (
        <div className="members-table-wrap">
          <table className="members-table" aria-label="Data sources">
            <thead>
              <tr>
                <th>Name</th>
                <th>Environment</th>
                <th>Status</th>
                <th>Database</th>
                <th>Last tested</th>
                <th>Last connected</th>
                {canManage ? <th>Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <DataSourceRow
                  key={item.id}
                  item={item}
                  canManage={canManage}
                  canDelete={canDelete}
                  onTest={() => setTesting(item)}
                  onEdit={() => setEditing(item)}
                  onReplaceCredentials={() => setReplacingCredentials(item)}
                  onDisable={() => setDisabling(item)}
                  onEnable={() => setEnabling(item)}
                  onDelete={() => setDeleting(item)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {adding ? (
        <AddConnectionDialog
          workspaceId={workspaceId}
          onClose={() => setAdding(false)}
          onSaved={refresh}
        />
      ) : null}
      {editing ? (
        <EditConnectionDialog
          workspaceId={workspaceId}
          dataSource={editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            await refresh();
            setEditing(null);
          }}
        />
      ) : null}
      {replacingCredentials ? (
        <ReplaceCredentialsDialog
          workspaceId={workspaceId}
          dataSource={replacingCredentials}
          onClose={() => setReplacingCredentials(null)}
          onReplaced={async () => {
            await refresh();
            setReplacingCredentials(null);
          }}
        />
      ) : null}
      {testing ? (
        <TestConnectionDialog
          workspaceId={workspaceId}
          dataSource={testing}
          onClose={async () => {
            await refresh();
            setTesting(null);
          }}
        />
      ) : null}
      {disabling ? (
        <DisableConfirmDialog
          workspaceId={workspaceId}
          dataSource={disabling}
          onClose={() => setDisabling(null)}
          onDisabled={async () => {
            await refresh();
            setDisabling(null);
          }}
        />
      ) : null}
      {enabling ? (
        <EnableConfirmDialog
          workspaceId={workspaceId}
          dataSource={enabling}
          onClose={() => setEnabling(null)}
          onEnabled={async () => {
            await refresh();
            setEnabling(null);
          }}
        />
      ) : null}
      {deleting ? (
        <DeleteConfirmDialog
          workspaceId={workspaceId}
          dataSource={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={async () => {
            await refresh();
            setDeleting(null);
          }}
        />
      ) : null}
    </div>
  );
}

function DataSourceRow({
  item,
  canManage,
  canDelete,
  onTest,
  onEdit,
  onReplaceCredentials,
  onDisable,
  onEnable,
  onDelete,
}: {
  item: DataSource;
  canManage: boolean;
  canDelete: boolean;
  onTest: () => void;
  onEdit: () => void;
  onReplaceCredentials: () => void;
  onDisable: () => void;
  onEnable: () => void;
  onDelete: () => void;
}) {
  const [revealed, setRevealed] = useState(false);
  const status = describeStatus(item.status, item.last_error_category);
  const environmentLabel = ENVIRONMENT_LABELS[item.environment as DataSourceEnvironment] ?? item.environment;

  return (
    <tr>
      <td>
        <div className="data-source-name-cell">
          <strong>{item.name}</strong>
          {item.description ? <span className="muted">{item.description}</span> : null}
        </div>
      </td>
      <td>
        <div className="data-source-badges">
          <span className={`badge badge-env-${item.environment}`}>{environmentLabel}</span>
          {item.environment === "production" ? (
            <span className="muted" style={{ fontSize: 11.5 }}>
              · Read only
            </span>
          ) : null}
        </div>
      </td>
      <td>
        <div className="data-source-badges">
          <span className={`badge ${status.className}`} title={item.last_connection_error ?? undefined}>
            {status.label}
          </span>
        </div>
        <span className="muted" style={{ fontSize: 11.5 }} title="Derived from the connection's onboarding progress, not a live check">
          {readOnlyLabel(item.status)}
        </span>
      </td>
      <td>
        <span title={revealed ? item.host : undefined}>
          {revealed ? item.host : maskHost(item.host)}
        </span>
        <br />
        <span className="muted">{item.database}</span>
        <br />
        <button
          type="button"
          className="btn btn-secondary btn-small"
          style={{ marginTop: 4, padding: "2px 8px", fontSize: 11 }}
          onClick={() => setRevealed((current) => !current)}
        >
          {revealed ? "Hide host" : "Show host"}
        </button>
      </td>
      <td title={item.last_connection_at ?? undefined}>{formatDateTime(item.last_connection_at)}</td>
      <td title={item.last_successful_connection_at ?? undefined}>
        {formatDateTime(item.last_successful_connection_at)}
      </td>
      {canManage ? (
        <td>
          <div className="members-actions" style={{ flexWrap: "wrap" }}>
            <button type="button" className="btn btn-secondary btn-small" onClick={onTest}>
              Test connection
            </button>
            <button type="button" className="btn btn-secondary btn-small" onClick={onEdit}>
              Edit
            </button>
            <button type="button" className="btn btn-secondary btn-small" onClick={onReplaceCredentials}>
              Replace credentials
            </button>
            {item.status === "disabled" ? (
              <button type="button" className="btn btn-secondary btn-small" onClick={onEnable}>
                Enable
              </button>
            ) : (
              <button type="button" className="btn btn-secondary btn-small" onClick={onDisable}>
                Disable
              </button>
            )}
            {canDelete ? (
              <button type="button" className="btn btn-danger btn-small" onClick={onDelete}>
                Delete
              </button>
            ) : null}
          </div>
        </td>
      ) : null}
    </tr>
  );
}

function TestResultView({ result }: { result: ConnectionTestResult }) {
  return (
    <div className={`form-banner ${result.success ? "success" : "error"}`} role={result.success ? "status" : "alert"}>
      <p style={{ margin: 0, fontWeight: 700 }}>
        {result.success ? "Connection succeeded" : "Connection failed"}
      </p>
      <p style={{ margin: "4px 0 0" }}>{result.message}</p>
      <dl className="test-result-grid">
        {result.server_version ? (
          <div>
            <dt>PostgreSQL version</dt>
            <dd>{result.server_version}</dd>
          </div>
        ) : null}
        <div>
          <dt>SSL</dt>
          <dd>{result.ssl_active === null ? "Unknown" : result.ssl_active ? "Active" : "Not active"}</dd>
        </div>
        {result.accessible_schemas.length > 0 ? (
          <div>
            <dt>Accessible schemas</dt>
            <dd>{result.accessible_schemas.join(", ")}</dd>
          </div>
        ) : null}
        {result.latency_ms !== null ? (
          <div>
            <dt>Latency</dt>
            <dd>{Math.round(result.latency_ms)} ms</dd>
          </div>
        ) : null}
        <div>
          <dt>Tested at</dt>
          <dd>{formatDateTime(result.tested_at)}</dd>
        </div>
      </dl>
    </div>
  );
}

function DataSourcesSkeleton() {
  return (
    <div className="members-table-wrap" aria-busy="true" aria-label="Loading data sources">
      {[0, 1, 2].map((row) => (
        <div className="skeleton-row" key={row}>
          <span className="skeleton-block" style={{ maxWidth: 160 }} />
          <span className="skeleton-block" style={{ maxWidth: 100 }} />
          <span className="skeleton-block" style={{ maxWidth: 100 }} />
          <span className="skeleton-block" style={{ maxWidth: 220 }} />
        </div>
      ))}
    </div>
  );
}

// -- test connection (an existing, already-saved connection) ----------------

function TestConnectionDialog({
  workspaceId,
  dataSource,
  onClose,
}: {
  workspaceId: string;
  dataSource: DataSource;
  onClose: () => Promise<void>;
}) {
  const [result, setResult] = useState<ConnectionTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const runTest = async () => {
    setBusy(true);
    setError(null);
    try {
      const outcome = await dataSourcesApi.testConnection(workspaceId, dataSource.id);
      setResult(outcome);
    } catch (submitError) {
      setError(errorMessage(submitError, "The connection could not be tested."));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    // Runs the real test-connection request as soon as the dialog opens, so
    // the caller sees a result without an extra click -- the state changes
    // happen asynchronously inside runTest's own `await`, not synchronously
    // in this effect body. Only ever auto-runs once, when the dialog opens
    // for this connection.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void runTest();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataSource.id]);

  return (
    <div className="modal-backdrop" onClick={() => void onClose()}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Test connection: ${dataSource.name}`}
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Test connection</h2>
        <p style={{ margin: 0, color: "var(--muted)" }}>{dataSource.name}</p>
        {busy && !result ? (
          <p className="progress">
            <span className="spinner" /> Testing…
          </p>
        ) : null}
        {error ? (
          <p className="form-banner error" role="alert">
            {error}
          </p>
        ) : null}
        {result ? <TestResultView result={result} /> : null}
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={runTest} disabled={busy}>
            {busy ? "Testing…" : "Test again"}
          </button>
          <button type="button" className="btn btn-primary" onClick={() => void onClose()}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// -- shared connection-detail fields (host/port/db/username/ssl/timeouts) --

type ConnectionDetailState = {
  host: string;
  port: string;
  database: string;
  username: string;
  sslMode: DataSourceSslMode;
  schema: string;
  sourceTimezone: string;
  statementTimeoutSeconds: string;
  connectionTimeoutSeconds: string;
  maxResultRows: string;
  maxResultBytes: string;
};

function defaultConnectionDetailState(): ConnectionDetailState {
  return {
    host: "",
    port: String(DEFAULT_PORT),
    database: "",
    username: "",
    sslMode: DEFAULT_SSL_MODE,
    schema: "public",
    sourceTimezone: "",
    statementTimeoutSeconds: String(DEFAULT_STATEMENT_TIMEOUT_SECONDS),
    connectionTimeoutSeconds: String(DEFAULT_CONNECTION_TIMEOUT_SECONDS),
    maxResultRows: String(DEFAULT_MAX_RESULT_ROWS),
    maxResultBytes: String(DEFAULT_MAX_RESULT_BYTES),
  };
}

function connectionDetailStateFrom(dataSource: DataSource): ConnectionDetailState {
  return {
    host: dataSource.host,
    port: String(dataSource.port),
    database: dataSource.database,
    username: dataSource.username,
    sslMode: dataSource.ssl_mode as DataSourceSslMode,
    schema: dataSource.allowed_schemas[0] ?? "public",
    sourceTimezone: dataSource.source_timezone ?? "",
    statementTimeoutSeconds: String(dataSource.statement_timeout_seconds),
    connectionTimeoutSeconds: String(dataSource.connection_timeout_seconds),
    maxResultRows: String(dataSource.max_result_rows),
    maxResultBytes: String(dataSource.max_result_bytes),
  };
}

/** Validates the shared field set and returns a field-name -> message map;
 * empty when the state is submittable. Mirrors the backend's own bounds
 * (app.datasources.contracts.DataSourceConnectionConfig) so a request is
 * never sent only to be rejected for a range the UI could have caught. */
function validateConnectionDetails(state: ConnectionDetailState): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!state.host.trim()) errors.host = "Host is required.";
  const port = Number(state.port);
  if (!Number.isInteger(port) || port < 1 || port > 65_535) errors.port = "Port must be between 1 and 65535.";
  if (!state.database.trim()) errors.database = "Database name is required.";
  if (!state.username.trim()) errors.username = "Username is required.";
  if (!state.schema.trim()) errors.schema = "At least one schema is required.";
  const statementTimeout = Number(state.statementTimeoutSeconds);
  if (!(statementTimeout > 0) || statementTimeout > 120) {
    errors.statementTimeoutSeconds = "Statement timeout must be between 0 and 120 seconds.";
  }
  const connectionTimeout = Number(state.connectionTimeoutSeconds);
  if (!(connectionTimeout > 0) || connectionTimeout > 60) {
    errors.connectionTimeoutSeconds = "Connection timeout must be between 0 and 60 seconds.";
  }
  const maxRows = Number(state.maxResultRows);
  if (!Number.isInteger(maxRows) || maxRows < 1 || maxRows > 50_000) {
    errors.maxResultRows = "Maximum rows must be between 1 and 50,000.";
  }
  const maxBytes = Number(state.maxResultBytes);
  if (!Number.isInteger(maxBytes) || maxBytes < 1_024) {
    errors.maxResultBytes = "Maximum result bytes must be at least 1,024.";
  }
  return errors;
}

function ConnectionDetailFields({
  state,
  onChange,
  errors,
  disabled,
}: {
  state: ConnectionDetailState;
  onChange: (next: ConnectionDetailState) => void;
  errors: Record<string, string>;
  disabled?: boolean;
}) {
  const set = <K extends keyof ConnectionDetailState>(key: K, value: ConnectionDetailState[K]) =>
    onChange({ ...state, [key]: value });

  return (
    <div className="settings-grid">
      <FormField
        id="ds-host"
        label="Host"
        value={state.host}
        onChange={(event) => set("host", event.target.value)}
        error={errors.host}
        disabled={disabled}
        required
      />
      <FormField
        id="ds-port"
        label="Port"
        type="number"
        min={1}
        max={65_535}
        value={state.port}
        onChange={(event) => set("port", event.target.value)}
        error={errors.port}
        disabled={disabled}
        required
      />
      <FormField
        id="ds-database"
        label="Database"
        value={state.database}
        onChange={(event) => set("database", event.target.value)}
        error={errors.database}
        disabled={disabled}
        required
      />
      <FormField
        id="ds-username"
        label="Username"
        value={state.username}
        onChange={(event) => set("username", event.target.value)}
        error={errors.username}
        disabled={disabled}
        required
      />
      <div className="field">
        <label htmlFor="ds-ssl-mode">SSL mode</label>
        <select
          id="ds-ssl-mode"
          value={state.sslMode}
          onChange={(event) => set("sslMode", event.target.value as DataSourceSslMode)}
          disabled={disabled}
        >
          {SSL_MODES.map((mode) => (
            <option key={mode} value={mode}>
              {mode}
            </option>
          ))}
        </select>
      </div>
      <FormField
        id="ds-timezone"
        label="Source timezone"
        value={state.sourceTimezone}
        onChange={(event) => set("sourceTimezone", event.target.value)}
        placeholder="e.g. UTC (optional)"
        disabled={disabled}
      />
      <FormField
        id="ds-schema"
        label="Initial allowed schema"
        value={state.schema}
        onChange={(event) => set("schema", event.target.value)}
        error={errors.schema}
        hint="Additional schemas and table selection are configured later, in the schema catalog."
        disabled={disabled}
        required
      />
      <FormField
        id="ds-statement-timeout"
        label="Statement timeout (seconds)"
        type="number"
        min={0}
        max={120}
        step="any"
        value={state.statementTimeoutSeconds}
        onChange={(event) => set("statementTimeoutSeconds", event.target.value)}
        error={errors.statementTimeoutSeconds}
        disabled={disabled}
      />
      <FormField
        id="ds-connection-timeout"
        label="Connection timeout (seconds)"
        type="number"
        min={0}
        max={60}
        step="any"
        value={state.connectionTimeoutSeconds}
        onChange={(event) => set("connectionTimeoutSeconds", event.target.value)}
        error={errors.connectionTimeoutSeconds}
        disabled={disabled}
      />
      <FormField
        id="ds-max-rows"
        label="Maximum rows"
        type="number"
        min={1}
        max={50_000}
        value={state.maxResultRows}
        onChange={(event) => set("maxResultRows", event.target.value)}
        error={errors.maxResultRows}
        disabled={disabled}
      />
      <FormField
        id="ds-max-bytes"
        label="Maximum result bytes"
        type="number"
        min={1_024}
        value={state.maxResultBytes}
        onChange={(event) => set("maxResultBytes", event.target.value)}
        error={errors.maxResultBytes}
        disabled={disabled}
      />
    </div>
  );
}

// -- add connection -----------------------------------------------------------
//
// Two phases, because the backend has no "test before it exists" workflow:
// POST .../test-connection requires an already-created data_source_id (see
// app/api/routes/datasources.py), so a connection must be saved before it
// can be tested at all -- this dialog never fabricates a client-side-only
// test. "Save and enable" does not call the real `/enable` endpoint: that
// transition only applies to a *disabled* connection
// (DataSourceOnboardingService.enable requires status == "disabled") and has
// no meaning for a brand-new draft, which always starts at "pending". Instead
// "Save and enable" chains create -> test-connection, the real next step
// that actually establishes connectivity, then shows the result in the same
// review phase "Save as draft" also lands on.

type AddPhase = "compose" | "review";

function AddConnectionDialog({
  workspaceId,
  onClose,
  onSaved,
}: {
  workspaceId: string;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [phase, setPhase] = useState<AddPhase>("compose");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [environment, setEnvironment] = useState<DataSourceEnvironment>(DEFAULT_ENVIRONMENT);
  const [password, setPassword] = useState("");
  const [details, setDetails] = useState<ConnectionDetailState>(defaultConnectionDetailState());
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<"draft" | "enable" | null>(null);
  const [created, setCreated] = useState<DataSource | null>(null);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  const buildRequest = (): DataSourceCreateRequest | null => {
    const errors = validateConnectionDetails(details);
    if (!name.trim()) errors.name = "Name is required.";
    if (!password) errors.password = "Password is required.";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return null;
    return {
      name: name.trim(),
      description: description.trim() || null,
      engine: "postgresql",
      environment,
      host: details.host.trim(),
      port: Number(details.port),
      database: details.database.trim(),
      username: details.username.trim(),
      password,
      ssl_mode: details.sslMode,
      allowed_schemas: [details.schema.trim()],
      statement_timeout_seconds: Number(details.statementTimeoutSeconds),
      connection_timeout_seconds: Number(details.connectionTimeoutSeconds),
      source_timezone: details.sourceTimezone.trim() || null,
      max_result_rows: Number(details.maxResultRows),
      max_result_bytes: Number(details.maxResultBytes),
    };
  };

  const save = async (mode: "draft" | "enable") => {
    setError(null);
    const body = buildRequest();
    if (!body) return;
    setSaving(mode);
    try {
      const connection = await dataSourcesApi.create(workspaceId, body);
      setCreated(connection);
      setPhase("review");
      if (mode === "enable") {
        setTesting(true);
        try {
          const result = await dataSourcesApi.testConnection(workspaceId, connection.id);
          setTestResult(result);
        } catch (testSubmitError) {
          setTestError(errorMessage(testSubmitError, "The connection could not be tested."));
        } finally {
          setTesting(false);
        }
      }
    } catch (submitError) {
      setError(errorMessage(submitError, "This data source could not be created."));
    } finally {
      setSaving(null);
    }
  };

  const runTest = async () => {
    if (!created) return;
    setTesting(true);
    setTestError(null);
    try {
      const result = await dataSourcesApi.testConnection(workspaceId, created.id);
      setTestResult(result);
    } catch (submitError) {
      setTestError(errorMessage(submitError, "The connection could not be tested."));
    } finally {
      setTesting(false);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
  };

  return (
    <div className="modal-backdrop" onClick={phase === "compose" ? onClose : undefined}>
      <div
        className="modal modal-wide"
        role="dialog"
        aria-modal="true"
        aria-label="Add a data source"
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Add a data source</h2>
        {phase === "compose" ? (
          <form onSubmit={onSubmit}>
            {error ? (
              <p className="form-banner error" role="alert">
                {error}
              </p>
            ) : null}
            <div className="settings-grid">
              <FormField
                id="ds-name"
                label="Name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                error={fieldErrors.name}
                required
              />
              <div className="field">
                <label htmlFor="ds-environment">Environment</label>
                <select
                  id="ds-environment"
                  value={environment}
                  onChange={(event) => setEnvironment(event.target.value as DataSourceEnvironment)}
                >
                  {ENVIRONMENTS.map((option) => (
                    <option key={option} value={option}>
                      {ENVIRONMENT_LABELS[option]}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field field-wide">
                <label htmlFor="ds-description">Description</label>
                <input
                  id="ds-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Optional"
                />
              </div>
            </div>

            <h3>Connection</h3>
            <ConnectionDetailFields state={details} onChange={setDetails} errors={fieldErrors} />
            <FormField
              id="ds-password"
              label="Password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={fieldErrors.password}
              required
            />
            <p className="field-hint">
              Testing requires saving the connection first -- the backend needs a stored, encrypted
              connection to test against. Choose &quot;Save and enable&quot; to save and immediately
              test it, or save as a draft and test it later from the list.
            </p>

            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving !== null}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void save("draft")}
                disabled={saving !== null}
              >
                {saving === "draft" ? "Saving…" : "Save as draft"}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void save("enable")}
                disabled={saving !== null}
              >
                {saving === "enable" ? "Saving…" : "Save and enable"}
              </button>
            </div>
          </form>
        ) : (
          <div>
            <p className="form-banner success" role="status">
              {created?.name} was saved as a draft.
            </p>
            {testing && !testResult ? (
              <p className="progress">
                <span className="spinner" /> Testing…
              </p>
            ) : null}
            {testError ? (
              <p className="form-banner error" role="alert">
                {testError}
              </p>
            ) : null}
            {testResult ? <TestResultView result={testResult} /> : null}
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={runTest} disabled={testing}>
                {testing ? "Testing…" : testResult ? "Test again" : "Test connection"}
              </button>
              <button type="button" className="btn btn-primary" onClick={() => void onSaved()}>
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// -- edit connection ------------------------------------------------------------

function detailsEqual(a: ConnectionDetailState, b: ConnectionDetailState): boolean {
  return (
    a.host === b.host &&
    a.port === b.port &&
    a.database === b.database &&
    a.username === b.username &&
    a.sslMode === b.sslMode &&
    a.schema === b.schema &&
    a.sourceTimezone === b.sourceTimezone &&
    a.statementTimeoutSeconds === b.statementTimeoutSeconds &&
    a.connectionTimeoutSeconds === b.connectionTimeoutSeconds &&
    a.maxResultRows === b.maxResultRows &&
    a.maxResultBytes === b.maxResultBytes
  );
}

function EditConnectionDialog({
  workspaceId,
  dataSource,
  onClose,
  onSaved,
}: {
  workspaceId: string;
  dataSource: DataSource;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const initialDetails = connectionDetailStateFrom(dataSource);
  const [name, setName] = useState(dataSource.name);
  const [description, setDescription] = useState(dataSource.description ?? "");
  const [environment, setEnvironment] = useState<DataSourceEnvironment>(
    dataSource.environment as DataSourceEnvironment,
  );
  const [details, setDetails] = useState<ConnectionDetailState>(initialDetails);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const configChanged = !detailsEqual(initialDetails, details);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const errors = configChanged ? validateConnectionDetails(details) : {};
    if (!name.trim()) errors.name = "Name is required.";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSaving(true);
    try {
      await dataSourcesApi.update(workspaceId, dataSource.id, {
        name: name.trim(),
        description: description.trim() || null,
        environment,
        ...(configChanged
          ? {
              host: details.host.trim(),
              port: Number(details.port),
              database: details.database.trim(),
              username: details.username.trim(),
              ssl_mode: details.sslMode,
              allowed_schemas: [details.schema.trim()],
              statement_timeout_seconds: Number(details.statementTimeoutSeconds),
              connection_timeout_seconds: Number(details.connectionTimeoutSeconds),
              source_timezone: details.sourceTimezone.trim() || null,
              max_result_rows: Number(details.maxResultRows),
              max_result_bytes: Number(details.maxResultBytes),
            }
          : {}),
      });
      await onSaved();
    } catch (submitError) {
      setError(errorMessage(submitError, "This data source could not be updated."));
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal modal-wide"
        role="dialog"
        aria-modal="true"
        aria-label={`Edit ${dataSource.name}`}
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Edit data source</h2>
        <form onSubmit={onSubmit}>
          {error ? (
            <p className="form-banner error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="settings-grid">
            <FormField
              id="ds-edit-name"
              label="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              error={fieldErrors.name}
              required
            />
            <div className="field">
              <label htmlFor="ds-edit-environment">Environment</label>
              <select
                id="ds-edit-environment"
                value={environment}
                onChange={(event) => setEnvironment(event.target.value as DataSourceEnvironment)}
              >
                {ENVIRONMENTS.map((option) => (
                  <option key={option} value={option}>
                    {ENVIRONMENT_LABELS[option]}
                  </option>
                ))}
              </select>
            </div>
            <div className="field field-wide">
              <label htmlFor="ds-edit-description">Description</label>
              <input
                id="ds-edit-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="ds-edit-password">Password</label>
            <input id="ds-edit-password" value="Password configured" disabled readOnly />
            <p className="field-hint">
              Use &quot;Replace credentials&quot; from the connection list to change it. It is never
              shown here.
            </p>
          </div>

          <h3>Connection</h3>
          {configChanged ? (
            <p className="connection-detail-warning">
              Changing these fields resets this connection to Draft and refreshes its pooled
              connection -- you&apos;ll need to test it (and re-activate it, if it was active)
              afterward.
            </p>
          ) : null}
          <ConnectionDetailFields state={details} onChange={setDetails} errors={fieldErrors} />

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -- replace credentials ---------------------------------------------------

function ReplaceCredentialsDialog({
  workspaceId,
  dataSource,
  onClose,
  onReplaced,
}: {
  workspaceId: string;
  dataSource: DataSource;
  onClose: () => void;
  onReplaced: () => Promise<void>;
}) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setFieldError(undefined);
    if (!password) {
      setFieldError("Enter a new password.");
      return;
    }
    if (password !== confirmPassword) {
      setFieldError("The passwords don't match.");
      return;
    }
    setSaving(true);
    try {
      await dataSourcesApi.replaceCredentials(workspaceId, dataSource.id, { password });
      await onReplaced();
    } catch (submitError) {
      setError(errorMessage(submitError, "The credentials could not be replaced."));
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Replace credentials: ${dataSource.name}`}
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Replace credentials</h2>
        <p style={{ margin: 0, color: "var(--muted)" }}>
          {dataSource.name} -- the previous password is never shown and cannot be recovered.
        </p>
        <form onSubmit={onSubmit}>
          {error ? (
            <p className="form-banner error" role="alert">
              {error}
            </p>
          ) : null}
          <FormField
            id="ds-replace-password"
            label="New password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={fieldError}
            required
          />
          <FormField
            id="ds-replace-password-confirm"
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />
          <p className="field-hint">
            This resets the connection to Draft and refreshes its pooled connection. Test it
            afterward to confirm the new credentials work.
          </p>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Replacing…" : "Replace credentials"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -- disable / enable / delete -----------------------------------------------

function DisableConfirmDialog({
  workspaceId,
  dataSource,
  onClose,
  onDisabled,
}: {
  workspaceId: string;
  dataSource: DataSource;
  onClose: () => void;
  onDisabled: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const disable = async () => {
    setBusy(true);
    setError(null);
    try {
      await dataSourcesApi.disable(workspaceId, dataSource.id);
      await onDisabled();
    } catch (submitError) {
      setError(errorMessage(submitError, "This data source could not be disabled."));
      setBusy(false);
    }
  };

  return (
    <ConfirmDialog
      title={`Disable ${dataSource.name}?`}
      description="New analysis runs will no longer be able to use this connection. Historical runs and reports that already used it remain accessible and unaffected."
      confirmLabel="Disable"
      danger={false}
      busy={busy}
      error={error}
      onConfirm={() => void disable()}
      onCancel={onClose}
    />
  );
}

function EnableConfirmDialog({
  workspaceId,
  dataSource,
  onClose,
  onEnabled,
}: {
  workspaceId: string;
  dataSource: DataSource;
  onClose: () => void;
  onEnabled: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enable = async () => {
    setBusy(true);
    setError(null);
    try {
      await dataSourcesApi.enable(workspaceId, dataSource.id);
      await onEnabled();
    } catch (submitError) {
      setError(errorMessage(submitError, "This data source could not be enabled."));
      setBusy(false);
    }
  };

  return (
    <ConfirmDialog
      title={`Enable ${dataSource.name}?`}
      description="This connection returns to Draft and must be tested (and re-activated, if it was active before) again -- it isn't trusted automatically after being disabled."
      confirmLabel="Enable"
      danger={false}
      busy={busy}
      error={error}
      onConfirm={() => void enable()}
      onCancel={onClose}
    />
  );
}

function DeleteConfirmDialog({
  workspaceId,
  dataSource,
  onClose,
  onDeleted,
}: {
  workspaceId: string;
  dataSource: DataSource;
  onClose: () => void;
  onDeleted: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      await dataSourcesApi.remove(workspaceId, dataSource.id);
      await onDeleted();
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 403) {
        setError("Only an owner can delete a data source.");
      } else {
        setError(errorMessage(submitError, "This data source could not be deleted."));
      }
      setBusy(false);
    }
  };

  return (
    <ConfirmDialog
      title={`Delete ${dataSource.name}?`}
      description="This soft-deletes the connection: it disappears from this list and can no longer be tested, edited, or used by any analysis. If any historical run or report used it, that history is preserved and stays accessible on its own."
      confirmText={dataSource.name}
      confirmLabel="Delete data source"
      busy={busy}
      error={error}
      onConfirm={() => void remove()}
      onCancel={onClose}
    />
  );
}
