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

type LeftNavProps = {
  id?: string;
  mobileOpen?: boolean;
  onNavigate?: () => void;
};

export default function LeftNav({
  id,
  mobileOpen = false,
  onNavigate,
}: LeftNavProps) {
  const pathname = usePathname();

  return (
    <aside
      id={id}
      className={`fixed left-0 top-0 z-50 flex h-screen w-[min(18rem,88vw)] flex-col border-r-0 bg-surface p-5 shadow-2xl transition-transform duration-200 ease-out sm:p-6 md:z-40 md:w-72 md:translate-x-0 md:shadow-none ${
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      }`}
      aria-label="Main navigation"
    >
      <div className="mb-8 text-xl font-extrabold tracking-tight text-white">
        Gov Intelligence
      </div>

      <nav className="flex-1 space-y-2" role="navigation">
        {navItems.map(({ label, href, icon }) => {
          const isActive = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-full px-5 py-3 text-sm font-medium transition-all duration-200 sm:px-6 ${
                isActive
                  ? "bg-primary-container text-white shadow-[0_0_20px_rgba(98,0,238,0.3)]"
                  : "text-on-surface-variant hover:bg-surface-container-high hover:text-white"
              }`}
              aria-current={isActive ? "page" : undefined}
              onClick={() => onNavigate?.()}
            >
              <MaterialIcon name={icon} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
