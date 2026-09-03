import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SettingsNav } from "./settings-nav";

let pathname = "/w/ws-1/settings/profile";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

describe("SettingsNav", () => {
  it("links to every settings section under the current workspace", () => {
    render(<SettingsNav workspaceId="ws-1" />);

    const nav = screen.getByRole("navigation", { name: "Settings" });
    const labels = [
      "Profile",
      "Security",
      "Organization",
      "Members",
      "Regional & data",
      "Report preferences",
      "Appearance",
      "Danger zone",
    ];
    for (const label of labels) {
      const link = screen.getByRole("link", { name: label });
      expect(nav).toContainElement(link);
      expect(link).toHaveAttribute("href", expect.stringContaining("/w/ws-1/settings/"));
    }
  });

  it("marks the current section as the active page for assistive tech", () => {
    pathname = "/w/ws-1/settings/security";
    render(<SettingsNav workspaceId="ws-1" />);

    expect(screen.getByRole("link", { name: "Security" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Profile" })).not.toHaveAttribute("aria-current");
  });
});
