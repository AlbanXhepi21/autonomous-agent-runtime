"use client";

import { useEffect, useState } from "react";
import { readStoredTheme, storeTheme, type ThemePreference } from "@/lib/appearance/theme";

const OPTIONS: { value: ThemePreference; label: string; swatchClass: string }[] = [
  { value: "system", label: "Match system", swatchClass: "theme-swatch-system" },
  { value: "light", label: "Light", swatchClass: "theme-swatch-light" },
  { value: "dark", label: "Dark", swatchClass: "theme-swatch-dark" },
];

export function AppearanceSettings() {
  const [theme, setTheme] = useState<ThemePreference>("system");

  useEffect(() => {
    // Reads localStorage, so this can only run after mount -- rendering
    // "system" on the very first client render deliberately matches the
    // server-rendered markup, then this corrects it a frame later. Reading
    // the stored value straight into useState's initializer would read it
    // during that first render too and mismatch the server's output.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(readStoredTheme());
  }, []);

  const choose = (value: ThemePreference) => {
    setTheme(value);
    storeTheme(value);
  };

  return (
    <div className="settings-page">
      <div className="settings-page-header">
        <h2>Appearance</h2>
        <p>Controls the color theme of this application on this device only.</p>
      </div>
      <div className="settings-section">
        <h3>Theme</h3>
        <p className="settings-section-desc">
          Applies to sign-in, settings, and the workbench shell. A few parts of the analysis
          workspace don&apos;t fully adapt to dark mode yet.
        </p>
        <div className="theme-picker" role="radiogroup" aria-label="Theme">
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={theme === option.value}
              className={`theme-option${theme === option.value ? " active" : ""}`}
              onClick={() => choose(option.value)}
            >
              <span className={`theme-swatch ${option.swatchClass}`} aria-hidden="true" />
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
