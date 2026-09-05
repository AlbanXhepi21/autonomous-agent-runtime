import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PersonalSettingsShell } from "./personal-settings-shell";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings/profile" }));

afterEach(() => {
  document.cookie = "last_workspace_id=; path=/; max-age=0";
});

describe("PersonalSettingsShell", () => {
  it("renders the two-pane settings shell without requiring any workspace prop", () => {
    render(
      <PersonalSettingsShell>
        <p>page content</p>
      </PersonalSettingsShell>,
    );

    expect(screen.getByRole("heading", { name: "Personal settings" })).toBeInTheDocument();
    expect(screen.getByText(/across every organization you belong to/)).toBeInTheDocument();
    const shell = screen.getByText("page content").closest(".settings-shell");
    expect(shell).not.toBeNull();
    expect(shell?.querySelector(".settings-nav")).not.toBeNull();
  });

  it("sends the back link to the remembered workspace when one exists", async () => {
    document.cookie = "last_workspace_id=ws-9; path=/";

    render(
      <PersonalSettingsShell>
        <p>page content</p>
      </PersonalSettingsShell>,
    );

    expect(await screen.findByRole("link", { name: /back to workbench/i })).toHaveAttribute(
      "href",
      "/w/ws-9",
    );
  });

  it("falls back to the tenant chooser when no workspace is remembered", () => {
    render(
      <PersonalSettingsShell>
        <p>page content</p>
      </PersonalSettingsShell>,
    );

    expect(screen.getByRole("link", { name: /back to workbench/i })).toHaveAttribute("href", "/");
  });
});
