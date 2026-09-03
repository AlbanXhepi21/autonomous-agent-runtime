"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner, FormField } from "@/components/ui/form-field";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";

const MIN_PASSWORD_LENGTH = 8;

export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ password?: string; confirmPassword?: string }>(
    {},
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!token) {
    return (
      <AuthCard eyebrow="Data Analyst" title="Link invalid">
        <FormBanner kind="error">
          This password reset link is missing its token. Request a new one.
        </FormBanner>
        <div className="auth-links">
          <Link href="/forgot-password">Request a new link</Link>
        </div>
      </AuthCard>
    );
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const errors: typeof fieldErrors = {};
    if (password.length < MIN_PASSWORD_LENGTH)
      errors.password = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
    if (confirmPassword !== password) errors.confirmPassword = "Passwords do not match.";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await authApi.resetPassword({ token, new_password: password });
      router.push("/login?reset=1");
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_token") {
        setFormError(error.message);
      } else if (error instanceof ApiError && error.code === "weak_password") {
        setFieldErrors((current) => ({ ...current, password: error.message }));
      } else {
        setFormError("Password could not be reset. Try again.");
      }
      setSubmitting(false);
    }
  };

  return (
    <AuthCard eyebrow="Data Analyst" title="Choose a new password">
      {formError ? <FormBanner kind="error">{formError}</FormBanner> : null}
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <FormField
          id="password"
          label="New password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
          hint={!fieldErrors.password ? `At least ${MIN_PASSWORD_LENGTH} characters.` : undefined}
          required
        />
        <FormField
          id="confirm-password"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={fieldErrors.confirmPassword}
          required
        />
        <button className="auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Resetting…" : "Reset password"}
        </button>
      </form>
    </AuthCard>
  );
}
