import type { InputHTMLAttributes, ReactNode } from "react";

export function FormField({
  id,
  label,
  error,
  hint,
  ...inputProps
}: {
  id: string;
  label: string;
  error?: string | null;
  hint?: string;
} & InputHTMLAttributes<HTMLInputElement>) {
  const errorId = error ? `${id}-error` : undefined;
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={[errorId, hintId].filter(Boolean).join(" ") || undefined}
        {...inputProps}
      />
      {hint ? (
        <p className="field-hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="field-error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function FormBanner({ kind, children }: { kind: "error" | "success"; children: ReactNode }) {
  return (
    <p className={`form-banner ${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}
