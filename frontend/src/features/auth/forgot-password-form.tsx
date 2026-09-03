"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner, FormField } from "@/components/ui/form-field";
import { authApi } from "@/lib/api/auth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!EMAIL_PATTERN.test(email)) {
      setFieldError("Enter a valid email address.");
      return;
    }
    setFieldError(undefined);
    setSubmitting(true);
    try {
      // The backend replies identically whether or not the address is
      // registered, so this call cannot itself reveal account existence --
      // shown on success or failure alike, network errors included.
      await authApi.forgotPassword({ email });
    } catch {
      // Intentionally ignored; see above.
    } finally {
      setSubmitting(false);
      setSent(true);
    }
  };

  if (sent) {
    return (
      <AuthCard eyebrow="Data Analyst" title="Check your email">
        <FormBanner kind="success">
          If an account exists for {email}, we&apos;ve sent instructions to reset your password.
        </FormBanner>
        <div className="auth-links">
          <Link href="/login">Back to sign in</Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      eyebrow="Data Analyst"
      title="Reset your password"
      subtitle="Enter your email and we'll send you a reset link."
    >
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fieldError}
          required
        />
        <button className="auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <div className="auth-links">
        <Link href="/login">Back to sign in</Link>
      </div>
    </AuthCard>
  );
}
