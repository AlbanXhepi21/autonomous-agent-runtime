import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RevokedAccessRedirect } from "./revoked-access-redirect";
import { readLastWorkspaceId, rememberWorkspaceId } from "@/lib/auth/last-workspace";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

describe("RevokedAccessRedirect", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    rememberWorkspaceId("ws-revoked");
  });

  it("discards the remembered workspace and sends the caller back to the chooser", () => {
    render(<RevokedAccessRedirect />);

    expect(readLastWorkspaceId()).toBeNull();
    expect(replace).toHaveBeenCalledWith("/");
  });
});
