'use client'

import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { BottomNav } from './bottom-nav'

interface DashboardLayoutWrapperProps {
  children: React.ReactNode
}

/**
 * Client wrapper para o layout do dashboard.
 *
 * Sprint 44 T05.2: Separar lógica de pathname em componente client.
 * O layout pai pode ser Server Component, delegando a lógica client para cá.
 */
export function DashboardLayoutWrapper({ children }: DashboardLayoutWrapperProps) {
  const pathname = usePathname()
  const isChipsModule = pathname.startsWith('/chips')
  const isFullScreenPage = pathname === '/conversas'

  // O módulo de chips tem seu próprio layout com sidebar
  if (isChipsModule) {
    return <>{children}</>
  }

  return (
    <div className={cn('bg-secondary', isFullScreenPage ? 'h-screen overflow-hidden' : 'min-h-screen')}>
      {/* Sidebar - desktop only */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:w-64 lg:overflow-y-auto lg:border-r lg:border-border lg:bg-card">
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
