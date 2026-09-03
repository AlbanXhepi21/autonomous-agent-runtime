"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner } from "@/components/ui/form-field";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";

type Outcome =
  { status: "loading" } | { status: "error"; message: string } | { status: "confirmed" };

export function ConfirmEmailChange() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [outcome, setOutcome] = useState<Outcome>(() =>
    token
      ? { status: "loading" }
      : { status: "error", message: "This confirmation link is missing its token." },
  );
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;

    usersApi
      .confirmEmailChange({ token })
      .then((settings) => {
        setOutcome({ status: "confirmed" });
        // The backend revokes every session as part of the change, this
        // browser's included -- send the caller back to sign in rather than
        // pretend the current session is still valid.
        router.push(`/login?email-changed=1&email=${encodeURIComponent(settings.email)}`);
      })
      .catch((error: unknown) => {
        setOutcome({
          status: "error",
          message: error instanceof ApiError ? error.message : "This link could not be confirmed.",
        });
      });
  }, [token, router]);

  return (
    <AuthCard eyebrow="Data Analyst" title="Confirm email change">
      {outcome.status === "loading" || outcome.status === "confirmed" ? (
        <p className="muted">Confirming…</p>
      ) : (
        <>
          <FormBanner kind="error">{outcome.message}</FormBanner>
          <div className="auth-links">
            <Link href="/">Continue</Link>
          </div>
        </>
      )}
    </AuthCard>
  );
}
