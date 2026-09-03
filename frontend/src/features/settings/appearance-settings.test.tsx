import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { AppearanceSettings } from "./appearance-settings";
import { THEME_STORAGE_KEY } from "@/lib/appearance/theme";

describe("AppearanceSettings", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });
  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("defaults to matching the system theme", () => {
    render(<AppearanceSettings />);

    const system = screen.getByRole("radio", { name: /Match system/ });
    expect(system).toHaveAttribute("aria-checked", "true");
  });

  it("applies and persists an explicit dark choice", () => {
    render(<AppearanceSettings />);

    fireEvent.click(screen.getByRole("radio", { name: "Dark" }));

    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("radio", { name: "Dark" })).toHaveAttribute("aria-checked", "true");
  });

  it("reflects a previously stored choice on mount", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    render(<AppearanceSettings />);

    expect(screen.getByRole("radio", { name: "Light" })).toHaveAttribute("aria-checked", "true");
  });

  it("clears the stored preference when system is chosen again", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    render(<AppearanceSettings />);

    fireEvent.click(screen.getByRole("radio", { name: /Match system/ }));

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("is a proper radiogroup for keyboard and screen-reader users", () => {
    render(<AppearanceSettings />);

    expect(screen.getByRole("radiogroup", { name: "Theme" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(3);
  });
});
