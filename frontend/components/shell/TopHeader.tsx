"use client";

type TopHeaderProps = {
  onMenuToggle?: () => void;
  menuOpen?: boolean;
};

export default function TopHeader({
  onMenuToggle,
  menuOpen = false,
}: TopHeaderProps) {
  return (
    <header className="sticky top-0 z-[60] flex min-h-16 w-full min-w-0 shrink-0 items-center justify-between border-b border-outline-variant/10 bg-surface-container-low/70 px-4 pt-[env(safe-area-inset-top,0px)] shadow-[0_0_40px_rgba(98,0,238,0.06)] backdrop-blur-3xl sm:min-h-[4.5rem] sm:px-6 md:min-h-20 md:border-b-0 md:px-8">
      <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3 md:flex-initial md:gap-8">
        <button
          type="button"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-white md:hidden"
          onClick={onMenuToggle}
          aria-expanded={menuOpen}
          aria-controls="app-sidebar"
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
        >
          <span className="material-symbols-outlined text-2xl">
            {menuOpen ? "close" : "menu"}
          </span>
        </button>
        <div className="truncate text-base font-bold tracking-tight text-white sm:text-lg">
          Intelligence Dashboard
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 sm:gap-6">
        <div className="flex items-center gap-2 rounded-full border border-secondary-container/20 bg-secondary-container/10 px-2 py-1.5 sm:px-3">
          <span
            className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-secondary"
            aria-hidden
          />
          <span className="text-[10px] font-bold whitespace-nowrap text-secondary sm:text-xs">
            <span className="hidden sm:inline">System Status: </span>
            Active
          </span>
        </div>
      </div>
    </header>
  );
}
