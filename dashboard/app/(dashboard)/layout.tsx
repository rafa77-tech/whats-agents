import { Sidebar } from "@/components/dashboard/sidebar";
import { Header } from "@/components/dashboard/header";
import { BottomNav } from "@/components/dashboard/bottom-nav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar - desktop only */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:w-64 lg:overflow-y-auto lg:bg-white lg:border-r lg:border-gray-200">
        <Sidebar />
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Header */}
        <Header />

        {/* Page content */}
        <main className="p-4 lg:p-6 pb-20 lg:pb-6">
          {children}
        </main>
      </div>

      {/* Bottom navigation - mobile only */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden">
        <BottomNav />
      </nav>
    </div>
  );
}
