/**
 * Chips Module Sidebar - Sprint 36
 *
 * Navegação lateral do módulo de chips.
 */

'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import type { Route } from 'next'
import { cn } from '@/lib/utils'
import {
  LucideIcon,
  LayoutDashboard,
  Cpu,
  AlertTriangle,
  Calendar,
  Settings,
  ChevronLeft,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'

interface NavItem {
  title: string
  href: string
  icon: LucideIcon
  exact?: boolean
  showBadge?: boolean
}

const navItems: NavItem[] = [
  {
    title: 'Visao Geral',
    href: '/chips',
    icon: LayoutDashboard,
    exact: true,
  },
  {
    title: 'Alertas',
    href: '/chips/alertas',
    icon: AlertTriangle,
    showBadge: true,
  },
  {
    title: 'Warmup',
    href: '/chips/warmup',
    icon: Calendar,
  },
  {
    title: 'Configuracoes',
    href: '/chips/configuracoes',
    icon: Settings,
  },
]

export function ChipsModuleSidebar() {
  const pathname = usePathname()
  const [criticalAlerts, setCriticalAlerts] = useState(0)

  useEffect(() => {
    const fetchAlertCount = async () => {
      try {
        const response = await fetch('/api/dashboard/chips/alerts/count')
        if (response.ok) {
          const data = await response.json()
          setCriticalAlerts(data.critical || 0)
        }
      } catch (error) {
        console.error('Error fetching alert count:', error)
      }
    }

    fetchAlertCount()
    const interval = setInterval(fetchAlertCount, 30000)
    return () => clearInterval(interval)
  }, [])

  const isActive = (href: string, exact?: boolean) => {
    if (exact) {
      return pathname === href
    }
    return pathname.startsWith(href)
  }

  return (
    <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:border-r lg:border-border lg:bg-card">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <Link
          href={'/dashboard' as Route}
          className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Dashboard
        </Link>
      </div>

      {/* Title */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2">
          <Cpu className="h-5 w-5 text-primary" />
          <h2 className="font-semibold text-foreground">Pool de Chips</h2>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href, item.exact)

          return (
            <Link
              key={item.href}
              href={item.href as Route}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              )}
            >
              <Icon className={cn('h-5 w-5', active ? 'text-primary' : 'text-muted-foreground')} />
              <span className="flex-1">{item.title}</span>
              {item.showBadge && criticalAlerts > 0 && (
                <Badge variant="destructive" className="h-5 min-w-[20px] px-1.5">
                  {criticalAlerts}
                </Badge>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-4 py-4">
        <p className="text-xs text-muted-foreground">Sistema Julia v2.0</p>
      </div>
    </aside>
  )
}
