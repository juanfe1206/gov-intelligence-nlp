import LeftNav from "@/components/shell/LeftNav";
import TopHeader from "@/components/shell/TopHeader";

export default function ShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <LeftNav />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto bg-surface">
          <div className="grid grid-cols-12 gap-6 p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
