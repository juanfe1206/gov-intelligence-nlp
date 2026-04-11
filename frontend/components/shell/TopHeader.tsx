"use client";

export default function TopHeader() {
  return (
    <header className="flex justify-between items-center w-full px-8 h-20 sticky top-0 z-50 bg-surface-container-low/70 backdrop-blur-3xl shadow-[0_0_40px_rgba(98,0,238,0.06)]">
      {/* Left Section */}
      <div className="flex items-center gap-8">
        <div className="text-lg font-bold tracking-tight text-white">
          Intelligence Dashboard
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-6">
        {/* System Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-secondary-container/10 rounded-full border border-secondary-container/20">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          <span className="text-xs text-secondary font-bold">System Status: Active</span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-4 text-on-surface-variant">
          <button className="material-symbols-outlined cursor-pointer hover:text-white transition-colors">
            notifications
          </button>
          <button className="material-symbols-outlined cursor-pointer hover:text-white transition-colors">
            settings
          </button>
          <div className="w-8 h-8 rounded-full overflow-hidden bg-surface-container-high border border-outline/20 flex items-center justify-center">
            <span className="material-symbols-outlined text-sm">person</span>
          </div>
        </div>
      </div>
    </header>
  );
}
