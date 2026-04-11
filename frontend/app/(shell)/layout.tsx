import LeftNav from "@/components/shell/LeftNav";
import TopHeader from "@/components/shell/TopHeader";

export default function ShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      <LeftNav />
      <div className="flex flex-col flex-1 overflow-hidden ml-72">
        <TopHeader />
        <main className="flex-1 overflow-y-auto bg-surface">
          <div className="p-8 space-y-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
