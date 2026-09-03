import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RegisterForm } from "./register-form";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

const push = vi.fn();

vi.mock("@/lib/api/auth", () => ({ authApi: { register: vi.fn() } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

function fillForm() {
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ada Lovelace" } });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse-1" } });
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: "correct-horse-1" },
  });
}

describe("RegisterForm", () => {
  beforeEach(() => vi.resetAllMocks());

  it("registers and redirects to login with a success flag", async () => {
    vi.mocked(authApi.register).mockResolvedValue({
      id: "u1",
      email: "ada@example.com",
      display_name: "Ada Lovelace",
      is_active: true,
      email_verified: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    });
    render(<RegisterForm />);
    fillForm();

    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() =>
      expect(authApi.register).toHaveBeenCalledWith({
        display_name: "Ada Lovelace",
        email: "ada@example.com",
        password: "correct-horse-1",
      }),
    );
    expect(push).toHaveBeenCalledWith("/login?registered=1");
  });

  it("rejects a mismatched password confirmation without calling the API", async () => {
    render(<RegisterForm />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ada Lovelace" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse-1" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), {
      target: { value: "different-password" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Passwords do not match.")).toBeInTheDocument();
    expect(authApi.register).not.toHaveBeenCalled();
  });

  it("attaches a duplicate-email error to the email field", async () => {
    vi.mocked(authApi.register).mockRejectedValue(
      new ApiError("An account with that email already exists.", 409, "email_already_registered"),
    );
    render(<RegisterForm />);
    fillForm();

    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByText("An account with that email already exists."),
    ).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
