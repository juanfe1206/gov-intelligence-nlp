"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import LeftNav from "@/components/shell/LeftNav";
import TopHeader from "@/components/shell/TopHeader";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const id = window.setTimeout(() => setMobileNavOpen(false), 0);
    return () => window.clearTimeout(id);
  }, [pathname]);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileNavOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {mobileNavOpen ? (
        <button
          type="button"
          aria-label="Close menu"
          className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}
      <LeftNav
        id="app-sidebar"
        mobileOpen={mobileNavOpen}
        onNavigate={() => setMobileNavOpen(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden md:ml-72">
        <TopHeader
          onMenuToggle={() => setMobileNavOpen((open) => !open)}
          menuOpen={mobileNavOpen}
        />
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-surface">
          <div className="mx-auto max-w-[100vw] space-y-6 p-4 pb-[max(1.25rem,env(safe-area-inset-bottom))] sm:space-y-8 sm:p-6 md:p-8 md:pb-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
