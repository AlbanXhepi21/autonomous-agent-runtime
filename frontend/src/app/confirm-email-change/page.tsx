import { Suspense } from "react";
import { ConfirmEmailChange } from "@/features/auth/confirm-email-change";

export const metadata = { title: "Confirm email change — AI Data Analyst" };

export default function ConfirmEmailChangePage() {
  return (
    <Suspense>
      <ConfirmEmailChange />
    </Suspense>
  );
}
