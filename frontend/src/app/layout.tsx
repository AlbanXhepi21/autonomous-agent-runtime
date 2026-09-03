import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Data Analyst",
  description: "Internal Data Analyst Workbench",
};

// Mirrors src/lib/appearance/theme.ts's THEME_STORAGE_KEY -- inlined because
// it must run before any bundle loads, or the page paints the wrong theme
// for a frame. Failure is silent: an inaccessible localStorage (private
// browsing, disabled storage) just leaves the OS-preferred theme in effect.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("appearance-theme");
    if (stored === "light" || stored === "dark") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (_) {}
})();
`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Browser extensions (for example LanguageTool) can add attributes to the
  // document element before React hydrates. Limit suppression to this boundary.
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
