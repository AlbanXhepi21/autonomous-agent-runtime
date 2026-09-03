"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner, FormField } from "@/components/ui/form-field";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

type Fields = { displayName?: string; email?: string; password?: string; confirmPassword?: string };

export function RegisterForm() {
  const router = useRouter();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Fields>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const errors: Fields = {};
    if (!displayName.trim()) errors.displayName = "Enter your name.";
    if (!EMAIL_PATTERN.test(email)) errors.email = "Enter a valid email address.";
    if (password.length < MIN_PASSWORD_LENGTH)
      errors.password = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
    if (confirmPassword !== password) errors.confirmPassword = "Passwords do not match.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      await authApi.register({ display_name: displayName.trim(), email, password });
      router.push("/login?registered=1");
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_already_registered") {
        setFieldErrors((current) => ({ ...current, email: error.message }));
      } else if (error instanceof ApiError && error.code === "weak_password") {
        setFieldErrors((current) => ({ ...current, password: error.message }));
      } else {
        setFormError("Registration could not be completed. Try again.");
      }
      setSubmitting(false);
    }
  };

  return (
    <AuthCard
      eyebrow="Data Analyst"
      title="Create your account"
      subtitle="Get started in a few seconds."
    >
      {formError ? <FormBanner kind="error">{formError}</FormBanner> : null}
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <FormField
          id="display-name"
          label="Name"
          type="text"
          autoComplete="name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          error={fieldErrors.displayName}
          required
        />
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
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
          hint={!fieldErrors.password ? `At least ${MIN_PASSWORD_LENGTH} characters.` : undefined}
          required
        />
        <FormField
          id="confirm-password"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={fieldErrors.confirmPassword}
          required
        />
        <button className="auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <div className="auth-links">
        <span>
          Already have an account? <Link href="/login">Sign in</Link>
        </span>
      </div>
    </AuthCard>
  );
}
