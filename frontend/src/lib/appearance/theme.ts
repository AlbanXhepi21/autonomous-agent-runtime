export type ThemePreference = "system" | "light" | "dark";

/** Kept in sync by hand with the inline script in `src/app/layout.tsx`, which
 * can't import this module -- it must run before any bundle loads. */
export const THEME_STORAGE_KEY = "appearance-theme";

export function readStoredTheme(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : "system";
}

export function applyTheme(theme: ThemePreference): void {
  if (typeof document === "undefined") return;
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}

export function storeTheme(theme: ThemePreference): void {
  if (typeof window === "undefined") return;
  if (theme === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
  else window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  applyTheme(theme);
}
