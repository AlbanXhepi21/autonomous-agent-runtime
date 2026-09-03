import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ResetPasswordForm } from "./reset-password-form";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

const push = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("@/lib/api/auth", () => ({ authApi: { resetPassword: vi.fn() } }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => searchParams,
}));

describe("ResetPasswordForm", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    searchParams = new URLSearchParams({ token: "reset-token" });
  });

  it("explains a missing token without ever calling the API", () => {
    searchParams = new URLSearchParams();
    render(<ResetPasswordForm />);

    expect(screen.getByText(/missing its token/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reset password" })).not.toBeInTheDocument();
  });

  it("resets the password and redirects to login with a success flag", async () => {
    vi.mocked(authApi.resetPassword).mockResolvedValue({ message: "Password reset." });
    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-correct-horse-1" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-correct-horse-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() =>
      expect(authApi.resetPassword).toHaveBeenCalledWith({
        token: "reset-token",
        new_password: "new-correct-horse-1",
      }),
    );
    expect(push).toHaveBeenCalledWith("/login?reset=1");
  });

  it("rejects a mismatched confirmation before calling the API", () => {
    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-correct-horse-1" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "something-else-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));

    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
    expect(authApi.resetPassword).not.toHaveBeenCalled();
  });

  it("shows an invalid-token error from the backend", async () => {
    vi.mocked(authApi.resetPassword).mockRejectedValue(
      new ApiError("This link is invalid or has expired.", 400, "invalid_token"),
    );
    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-correct-horse-1" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "new-correct-horse-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reset password" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This link is invalid or has expired.",
    );
    expect(push).not.toHaveBeenCalled();
  });
});
