import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "./login-form";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

const push = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("@/lib/api/auth", () => ({ authApi: { login: vi.fn() } }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => searchParams,
}));

describe("LoginForm", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    searchParams = new URLSearchParams();
  });

  it("signs in and returns to the validated next path", async () => {
    searchParams = new URLSearchParams({ next: "/w/abc" });
    vi.mocked(authApi.login).mockResolvedValue({
      id: "u1",
      email: "ada@example.com",
      display_name: "Ada",
      is_active: true,
      email_verified: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    });
    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() =>
      expect(authApi.login).toHaveBeenCalledWith({
        email: "ada@example.com",
        password: "correct-horse-1",
      }),
    );
    expect(push).toHaveBeenCalledWith("/w/abc");
  });

  it("discards an unvalidated next path and falls back to /", async () => {
    searchParams = new URLSearchParams({ next: "https://evil.example.com" });
    vi.mocked(authApi.login).mockResolvedValue({
      id: "u1",
      email: "ada@example.com",
      display_name: "Ada",
      is_active: true,
      email_verified: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    });
    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("shows the backend's generic invalid-credentials message on failure", async () => {
    vi.mocked(authApi.login).mockRejectedValue(
      new ApiError("Invalid email or password.", 401, "invalid_credentials"),
    );
    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(push).not.toHaveBeenCalled();
  });

  it("validates fields locally before ever calling the API", async () => {
    render(<LoginForm />);

    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(authApi.login).not.toHaveBeenCalled();
  });
});
