"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SECTIONS = [
  { slug: "profile", label: "Profile" },
  { slug: "security", label: "Security" },
  { slug: "appearance", label: "Appearance" },
] as const;

/** Navigation for the account-wide, tenant-independent settings area --
 * see `personal-settings-shell.tsx` for why these pages never take a
 * `workspaceId`. */
export function PersonalSettingsNav() {
  const pathname = usePathname();

  return (
    <nav className="settings-nav" aria-label="Personal settings">
      <ul>
        {SECTIONS.map((section) => {
          const href = `/settings/${section.slug}`;
          const active = pathname === href;
          return (
            <li key={section.slug}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={active ? "active" : undefined}
              >
                {section.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
