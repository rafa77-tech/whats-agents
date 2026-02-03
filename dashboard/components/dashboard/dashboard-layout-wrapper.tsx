/**
 * DashboardLayoutWrapper - Sprint 45
 *
 * Client wrapper para o layout do dashboard.
 * Inclui CommandPaletteProvider para busca global e sidebar colapsavel.
 */

'use client'

import { useState, useEffect, createContext, useContext } from 'react'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { BottomNav } from './bottom-nav'
import { CommandPaletteProvider } from '@/components/command-palette'
import { Button } from '@/components/ui/button'
import { PanelLeftClose, PanelLeft } from 'lucide-react'

// Context para estado da sidebar
interface SidebarContextType {
  collapsed: boolean
  setCollapsed: (value: boolean) => void
  toggle: () => void
}

const SidebarContext = createContext<SidebarContextType | null>(null)

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error('useSidebar must be used within DashboardLayoutWrapper')
  }
  return context
}

interface DashboardLayoutWrapperProps {
  children: React.ReactNode
}

const SIDEBAR_COLLAPSED_KEY = 'sidebar-collapsed'

export function DashboardLayoutWrapper({ children }: DashboardLayoutWrapperProps) {
  const pathname = usePathname()
  const isFullScreenPage = pathname === '/conversas'

  // Estado da sidebar com persistencia em localStorage
  const [collapsed, setCollapsed] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    if (stored !== null) {
      setCollapsed(stored === 'true')
    }
  }, [])

  const handleSetCollapsed = (value: boolean) => {
    setCollapsed(value)
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(value))
  }

  const toggle = () => handleSetCollapsed(!collapsed)

  const sidebarContext: SidebarContextType = {
    collapsed,
    setCollapsed: handleSetCollapsed,
    toggle,
  }

  // Largura da sidebar
  const sidebarWidth = collapsed ? 'lg:w-0' : 'lg:w-64'
  const mainPadding = collapsed ? 'lg:pl-0' : 'lg:pl-64'

  return (
    <SidebarContext.Provider value={sidebarContext}>
      <CommandPaletteProvider>
        <div
          className={cn(
            'bg-background',
            isFullScreenPage ? 'h-screen overflow-hidden' : 'min-h-screen'
          )}
        >
          {/* Sidebar - desktop only */}
          <aside
            className={cn(
              'sidebar-bg-white hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:overflow-y-auto lg:border-r lg:border-border lg:transition-all lg:duration-300',
              sidebarWidth,
              collapsed && 'lg:overflow-hidden lg:border-r-0'
            )}
          >
            {!collapsed && <Sidebar />}
          </aside>

          {/* Toggle button - desktop only */}
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              className={cn(
                'fixed z-50 hidden h-8 w-8 rounded-full border border-border bg-background shadow-sm transition-all duration-300 hover:bg-muted lg:flex',
                collapsed ? 'left-4 top-4' : 'left-60 top-4'
              )}
              aria-label={collapsed ? 'Expandir sidebar' : 'Recolher sidebar'}
            >
              {collapsed ? (
                <PanelLeft className="h-4 w-4" />
              ) : (
                <PanelLeftClose className="h-4 w-4" />
              )}
            </Button>
          )}

          {/* Main content */}
          <div
            className={cn(
              'bg-secondary transition-all duration-300',
              mainPadding,
              isFullScreenPage && 'flex h-full flex-col'
            )}
          >
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
      </CommandPaletteProvider>
    </SidebarContext.Provider>
  )
}
