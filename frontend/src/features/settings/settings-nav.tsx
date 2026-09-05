"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SECTIONS = [
  { slug: "organization", label: "General" },
  { slug: "members", label: "Members" },
  { slug: "data-sources", label: "Data Sources" },
  { slug: "regional", label: "Regional & data" },
  { slug: "reports", label: "Report preferences" },
  { slug: "danger", label: "Danger zone" },
] as const;

export function SettingsNav({ workspaceId }: { workspaceId: string }) {
  const pathname = usePathname();

  return (
    <nav className="settings-nav" aria-label="Settings">
      <ul>
        {SECTIONS.map((section) => {
          const href = `/w/${workspaceId}/settings/${section.slug}`;
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
