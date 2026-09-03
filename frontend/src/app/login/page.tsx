import { Suspense } from "react";
import { LoginForm } from "@/features/auth/login-form";

export const metadata = { title: "Sign in — AI Data Analyst" };

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
