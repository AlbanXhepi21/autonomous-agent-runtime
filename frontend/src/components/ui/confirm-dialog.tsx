"use client";

import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

/**
 * A shared confirmation modal for destructive actions. When `confirmText`
 * is given, the confirm button stays disabled until the caller retypes it
 * exactly -- used for the highest-stakes actions (deactivate, transfer).
 */
export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  confirmText,
  danger = true,
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  /** If set, the caller must type this exact value before confirming is allowed. */
  confirmText?: string;
  danger?: boolean;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [typed, setTyped] = useState("");
  const headingId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKeyDown);
    dialogRef.current?.focus();
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  const canConfirm = !busy && (confirmText === undefined || typed === confirmText);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (canConfirm) onConfirm();
  };

  return createPortal(
    <div className="modal-backdrop" onClick={onCancel}>
      <div
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={headingId}
        tabIndex={-1}
        ref={dialogRef}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={headingId}>{title}</h2>
        <p>{description}</p>
        <form onSubmit={onSubmit}>
          {confirmText ? (
            <div className="modal-confirm-field">
              <label htmlFor="confirm-typed">
                Type <strong>{confirmText}</strong> to confirm
              </label>
              <input
                id="confirm-typed"
                type="text"
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                autoComplete="off"
              />
            </div>
          ) : null}
          {error ? (
            <p className="form-banner error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
              Cancel
            </button>
            <button
              type="submit"
              className={danger ? "btn btn-danger" : "btn btn-primary"}
              disabled={!canConfirm}
            >
              {busy ? "Working…" : confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
