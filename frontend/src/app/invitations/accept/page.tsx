import { Suspense } from "react";
import { AcceptInvitation } from "@/features/auth/accept-invitation";

export const metadata = { title: "Accept invitation — AI Data Analyst" };

export default function AcceptInvitationPage() {
  return (
    <Suspense>
      <AcceptInvitation />
    </Suspense>
  );
}
