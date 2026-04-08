"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "📊" },
  { label: "Q&A", href: "/qa", icon: "💬" },
  { label: "Admin", href: "/admin", icon: "⚙️" },
];

export default function LeftNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col w-64 h-full bg-surface border-r border-border px-4 py-6 gap-1">
      {navItems.map(({ label, href, icon }) => {
        const isActive = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 ${
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted hover:bg-border hover:text-foreground"
            }`}
            aria-current={isActive ? "page" : undefined}
          >
            <span aria-hidden="true">{icon}</span>
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
