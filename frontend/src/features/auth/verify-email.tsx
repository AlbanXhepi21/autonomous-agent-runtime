"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner } from "@/components/ui/form-field";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";

type Outcome =
  { status: "loading" } | { status: "error"; message: string } | { status: "verified" };

export function VerifyEmail() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [outcome, setOutcome] = useState<Outcome>(() =>
    token
      ? { status: "loading" }
      : { status: "error", message: "This verification link is missing its token." },
  );
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;

    authApi
      .confirmEmailVerification({ token })
      .then(() => setOutcome({ status: "verified" }))
      .catch((error: unknown) => {
        setOutcome({
          status: "error",
          message: error instanceof ApiError ? error.message : "This link could not be confirmed.",
        });
      });
  }, [token]);

  return (
    <AuthCard eyebrow="Data Analyst" title="Verify your email">
      {outcome.status === "loading" ? <p className="muted">Confirming…</p> : null}
      {outcome.status === "verified" ? (
        <>
          <FormBanner kind="success">Your email address is verified.</FormBanner>
          <div className="auth-links">
            <Link href="/">Continue</Link>
          </div>
        </>
      ) : null}
      {outcome.status === "error" ? (
        <>
          <FormBanner kind="error">{outcome.message}</FormBanner>
          <div className="auth-links">
            <Link href="/">Continue</Link>
          </div>
        </>
      ) : null}
    </AuthCard>
  );
}
