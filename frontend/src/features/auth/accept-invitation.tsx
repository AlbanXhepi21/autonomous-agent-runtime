"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/ui/auth-card";
import { FormBanner } from "@/components/ui/form-field";
import { ApiError } from "@/lib/api/client";
import { workspacesApi } from "@/lib/api/workspaces";
import { rememberWorkspaceId } from "@/lib/auth/last-workspace";
import { LOGIN_RETURN_PARAM, sanitizeReturnPath } from "@/lib/auth/return-path";

type Outcome =
  { status: "loading" } | { status: "error"; message: string } | { status: "accepted" };

export function AcceptInvitation() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [outcome, setOutcome] = useState<Outcome>(() =>
    token
      ? { status: "loading" }
      : { status: "error", message: "This invitation link is missing its token." },
  );
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;

    workspacesApi
      .acceptInvitation({ token })
      .then((membership) => {
        rememberWorkspaceId(membership.workspace_id);
        setOutcome({ status: "accepted" });
        router.push(`/w/${membership.workspace_id}`);
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          const here = sanitizeReturnPath(`/invitations/accept?token=${encodeURIComponent(token)}`);
          router.push(`/login?${LOGIN_RETURN_PARAM}=${encodeURIComponent(here)}`);
          return;
        }
        const message =
          error instanceof ApiError
            ? error.message
            : "This invitation could not be accepted. Try again.";
        setOutcome({ status: "error", message });
      });
  }, [token, router]);

  return (
    <AuthCard eyebrow="Data Analyst" title="Joining workspace">
      {outcome.status === "loading" || outcome.status === "accepted" ? (
        <p className="muted">Accepting your invitation…</p>
      ) : (
        <>
          <FormBanner kind="error">{outcome.message}</FormBanner>
          <div className="auth-links">
            <Link href="/">Go to your workspaces</Link>
          </div>
        </>
      )}
    </AuthCard>
  );
}
