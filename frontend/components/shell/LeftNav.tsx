"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "dashboard" },
  { label: "Q&A", href: "/qa", icon: "chat_bubble" },
  { label: "Admin", href: "/admin", icon: "settings" },
];

function MaterialIcon({ name }: { name: string }) {
  return (
    <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
      {name}
    </span>
  );
}

export default function LeftNav() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen flex flex-col p-6 z-40 bg-surface w-72 rounded-r-none border-r-0">
      {/* Logo */}
      <div className="text-xl font-extrabold text-white mb-8 tracking-tight">
        Gov Intelligence
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 space-y-2">
        {navItems.map(({ label, href, icon }) => {
          const isActive = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-6 py-3 rounded-full transition-all duration-200 font-medium text-sm
                ${isActive
                  ? "bg-primary-container text-white shadow-[0_0_20px_rgba(98,0,238,0.3)]"
                  : "text-on-surface-variant hover:bg-surface-container-high hover:text-white"
                }`}
              aria-current={isActive ? "page" : undefined}
            >
              <MaterialIcon name={icon} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="mt-auto space-y-2 pt-6">
        <Link
          href="#"
          className="flex items-center gap-3 text-on-surface-variant px-6 py-3 hover:bg-surface-container-high hover:text-white rounded-full transition-colors font-medium text-sm"
        >
          <MaterialIcon name="help_outline" />
          <span>Support</span>
        </Link>
      </div>
    </aside>
  );
}
