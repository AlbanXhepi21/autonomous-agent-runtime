"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner, FormField } from "@/components/ui/form-field";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";
import { LOGIN_RETURN_PARAM, sanitizeReturnPath } from "@/lib/auth/return-path";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Statuses whose backend message is already written to be safe to show verbatim. */
const SAFE_TO_SHOW_STATUS = new Set([400, 401, 403, 422, 429]);

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = sanitizeReturnPath(searchParams.get(LOGIN_RETURN_PARAM));
  const sessionExpired = searchParams.get("expired") === "1";
  const justRegistered = searchParams.get("registered") === "1";
  const justReset = searchParams.get("reset") === "1";
  const emailChanged = searchParams.get("email-changed") === "1";
  const changedEmail = searchParams.get("email");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const errors: typeof fieldErrors = {};
    if (!EMAIL_PATTERN.test(email)) errors.email = "Enter a valid email address.";
    if (!password) errors.password = "Enter your password.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      await authApi.login({ email, password });
      router.push(returnTo);
    } catch (error) {
      setFormError(
        error instanceof ApiError && error.status && SAFE_TO_SHOW_STATUS.has(error.status)
          ? error.message
          : "Sign-in could not be completed. Try again.",
      );
      setSubmitting(false);
    }
  };

  return (
    <AuthCard
      eyebrow="Data Analyst"
      title="Sign in"
      subtitle="Sign in to continue to your workspace."
    >
      {sessionExpired ? (
        <FormBanner kind="error">Your session has expired. Sign in again.</FormBanner>
      ) : null}
      {justRegistered && !formError ? (
        <FormBanner kind="success">Account created. Sign in to continue.</FormBanner>
      ) : null}
      {justReset && !formError ? (
        <FormBanner kind="success">Password reset. Sign in with your new password.</FormBanner>
      ) : null}
      {emailChanged && !formError ? (
        <FormBanner kind="success">
          Your email is now {changedEmail ?? "updated"}. Sign in to continue.
        </FormBanner>
      ) : null}
      {formError ? <FormBanner kind="error">{formError}</FormBanner> : null}
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fieldErrors.email}
          required
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
          required
        />
        <button className="auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="auth-links">
        <Link href="/forgot-password">Forgot your password?</Link>
        <span>
          No account? <Link href="/register">Create one</Link>
        </span>
      </div>
    </AuthCard>
  );
}
