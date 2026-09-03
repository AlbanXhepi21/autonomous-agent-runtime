import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ForgotPasswordForm } from "./forgot-password-form";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

vi.mock("@/lib/api/auth", () => ({ authApi: { forgotPassword: vi.fn() } }));

describe("ForgotPasswordForm", () => {
  beforeEach(() => vi.resetAllMocks());

  it("shows the same confirmation whether or not the address is registered", async () => {
    vi.mocked(authApi.forgotPassword).mockResolvedValue({
      message: "If an account exists for that email, we've sent instructions.",
    });
    render(<ForgotPasswordForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByText(/If an account exists for ada@example.com/)).toBeInTheDocument();
  });

  it("shows the same confirmation even when the request itself fails", async () => {
    vi.mocked(authApi.forgotPassword).mockRejectedValue(
      new ApiError("Too many attempts.", 429, "rate_limited"),
    );
    render(<ForgotPasswordForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByText(/If an account exists for ada@example.com/)).toBeInTheDocument();
  });

  it("validates the email format before submitting", () => {
    render(<ForgotPasswordForm />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(authApi.forgotPassword).not.toHaveBeenCalled();
  });
});
