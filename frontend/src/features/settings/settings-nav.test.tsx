import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SettingsNav } from "./settings-nav";

let pathname = "/w/ws-1/settings/organization";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

describe("SettingsNav", () => {
  it("links to every organization settings section under the current workspace", () => {
    render(<SettingsNav workspaceId="ws-1" />);

    const nav = screen.getByRole("navigation", { name: "Settings" });
    const labels = [
      "General",
      "Members",
      "Data Sources",
      "Regional & data",
      "Report preferences",
      "Danger zone",
    ];
    for (const label of labels) {
      const link = screen.getByRole("link", { name: label });
      expect(nav).toContainElement(link);
      expect(link).toHaveAttribute("href", expect.stringContaining("/w/ws-1/settings/"));
    }
  });

  it("never links to the personal settings area -- that lives outside any workspace", () => {
    render(<SettingsNav workspaceId="ws-1" />);

    for (const label of ["Profile", "Security", "Appearance"]) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });

  it("marks the current section as the active page for assistive tech", () => {
    pathname = "/w/ws-1/settings/members";
    render(<SettingsNav workspaceId="ws-1" />);

    expect(screen.getByRole("link", { name: "Members" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "General" })).not.toHaveAttribute("aria-current");
  });
});
