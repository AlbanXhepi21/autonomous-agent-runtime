import type { ReactNode } from "react";
import { useSettings } from "./settings-context";

/**
 * Mirrors `SettingsBody` in settings-shell.tsx: in production, a settings
 * page is only ever mounted once `SettingsProvider` has finished loading,
 * so pages read `workspace`/`role` into local state unconditionally on
 * mount. Tests that render a page directly under `SettingsProvider` need
 * this same gate, or the page mounts while `workspace` is still null and
 * seeds its form state from nothing.
 */
export function SettingsLoadedGate({ children }: { children: ReactNode }) {
  const { loading, error } = useSettings();
  if (loading) return <p>loading</p>;
  if (error) return <p role="alert">{error}</p>;
  return children;
}
