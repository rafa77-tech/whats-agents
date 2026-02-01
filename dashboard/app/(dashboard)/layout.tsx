'use client'

import { usePathname } from 'next/navigation'
import { Sidebar } from '@/components/dashboard/sidebar'
import { Header } from '@/components/dashboard/header'
import { BottomNav } from '@/components/dashboard/bottom-nav'
import { cn } from '@/lib/utils'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isChipsModule = pathname.startsWith('/chips')
  const isFullScreenPage = pathname === '/conversas' // Pages that need full height without padding

  // O módulo de chips tem seu próprio layout com sidebar
  if (isChipsModule) {
    return <>{children}</>
  }

  return (
    <div
      className={cn('bg-gray-50', isFullScreenPage ? 'h-screen overflow-hidden' : 'min-h-screen')}
    >
      {/* Sidebar - desktop only */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:w-64 lg:overflow-y-auto lg:border-r lg:border-gray-200 lg:bg-white">
        <Sidebar />
      </aside>

      {/* Main content */}
      <div className={cn('lg:pl-64', isFullScreenPage && 'flex h-full flex-col')}>
        {/* Header */}
        <Header />

        {/* Page content */}
        <main
          className={cn(
            isFullScreenPage ? 'min-h-0 flex-1 overflow-hidden' : 'p-4 pb-20 lg:p-6 lg:pb-6'
          )}
        >
          {children}
        </main>
      </div>

      {/* Bottom navigation - mobile only */}
      {!isFullScreenPage && (
        <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden">
          <BottomNav />
        </nav>
      )}
    </div>
  )
}
