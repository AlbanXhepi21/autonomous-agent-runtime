import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { proxy } from "./proxy";

function requestFor(path: string, { sessionCookie }: { sessionCookie?: string } = {}) {
  const headers = sessionCookie ? { cookie: `session_token=${sessionCookie}` } : undefined;
  return new NextRequest(new URL(path, "http://localhost:3000"), { headers });
}

describe("proxy", () => {
  it("redirects an unauthenticated request for a protected page to /login with a return path", () => {
    const response = proxy(requestFor("/w/abc/settings?tab=general"));

    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location")!);
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("next")).toBe("/w/abc/settings?tab=general");
  });

  it("lets an authenticated request through to a protected page", () => {
    const response = proxy(requestFor("/w/abc", { sessionCookie: "s1" }));

    expect(response.headers.get("location")).toBeNull();
  });

  it("lets an unauthenticated request through to a public auth page", () => {
    const response = proxy(requestFor("/login"));

    expect(response.headers.get("location")).toBeNull();
  });

  it("lets an unauthenticated request through to the invitation-acceptance page", () => {
    const response = proxy(requestFor("/invitations/accept?token=abc"));

    expect(response.headers.get("location")).toBeNull();
  });

  it("lets an unauthenticated request through to the email-verification confirmation page", () => {
    const response = proxy(requestFor("/verify-email?token=abc"));

    expect(response.headers.get("location")).toBeNull();
  });

  it("lets an already-authenticated request through to confirm an email change too", () => {
    const response = proxy(requestFor("/confirm-email-change?token=abc", { sessionCookie: "s1" }));

    expect(response.headers.get("location")).toBeNull();
  });

  it("sends an already-authenticated visitor away from /login", () => {
    const response = proxy(requestFor("/login", { sessionCookie: "s1" }));

    expect(response.status).toBe(307);
    expect(new URL(response.headers.get("location")!).pathname).toBe("/");
  });

  it("sends an already-authenticated visitor away from /register", () => {
    const response = proxy(requestFor("/register", { sessionCookie: "s1" }));

    expect(response.status).toBe(307);
    expect(new URL(response.headers.get("location")!).pathname).toBe("/");
  });

  it("does not redirect an authenticated visitor away from /forgot-password", () => {
    const response = proxy(requestFor("/forgot-password", { sessionCookie: "s1" }));

    expect(response.headers.get("location")).toBeNull();
  });
});
