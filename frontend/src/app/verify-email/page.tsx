import { Suspense } from "react";
import { VerifyEmail } from "@/features/auth/verify-email";

export const metadata = { title: "Verify email — AI Data Analyst" };

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
