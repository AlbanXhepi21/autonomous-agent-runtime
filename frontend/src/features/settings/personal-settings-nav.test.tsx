import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PersonalSettingsNav } from "./personal-settings-nav";

let pathname = "/settings/profile";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

describe("PersonalSettingsNav", () => {
  it("links to every personal settings section, never a workspace-scoped path", () => {
    render(<PersonalSettingsNav />);

    const nav = screen.getByRole("navigation", { name: "Personal settings" });
    for (const label of ["Profile", "Security", "Appearance"]) {
      const link = screen.getByRole("link", { name: label });
      expect(nav).toContainElement(link);
      expect(link).toHaveAttribute("href", expect.stringMatching(/^\/settings\//));
    }
  });

  it("never links to organization administration", () => {
    render(<PersonalSettingsNav />);

    for (const label of ["Members", "Danger zone", "Report preferences", "General"]) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });

  it("marks the current section as the active page for assistive tech", () => {
    pathname = "/settings/security";
    render(<PersonalSettingsNav />);

    expect(screen.getByRole("link", { name: "Security" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Profile" })).not.toHaveAttribute("aria-current");
  });
});
