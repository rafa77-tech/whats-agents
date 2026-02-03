/**
 * BottomNav - Sprint 45
 *
 * Navegacao inferior para mobile com acesso rapido
 * as funcionalidades mais usadas + drawer completo.
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Megaphone,
  Smartphone,
  MessageSquare,
  type LucideIcon,
} from 'lucide-react'
import { MobileDrawer, MobileMenuButton } from './mobile-drawer'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
}

// 4 itens mais importantes + Menu
const navigation: NavItem[] = [
  { name: 'Home', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Conversas', href: '/conversas', icon: MessageSquare },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Chips', href: '/chips', icon: Smartphone },
]

export function BottomNav() {
  const pathname = usePathname()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const isActive = (href: string) => {
    return pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
  }

  return (
    <>
      <div className="safe-area-pb border-t border-border bg-card px-1 py-1.5">
        <nav className="flex items-center justify-around">
          {navigation.map((item) => {
            const active = isActive(item.href)
            return (
              <Link
                key={item.name}
                href={item.href as Route}
                className={cn(
                  'flex min-w-[56px] flex-col items-center gap-1 rounded-lg px-2 py-2 transition-colors',
                  active ? 'text-primary' : 'text-muted-foreground active:bg-muted'
                )}
              >
                <item.icon className={cn('h-6 w-6', active && 'text-primary')} />
                <span className={cn('text-[10px] font-medium', active && 'text-primary')}>
                  {item.name}
                </span>
              </Link>
            )
          })}
          <MobileMenuButton onClick={() => setDrawerOpen(true)} />
        </nav>
      </div>
      <MobileDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
    </>
  )
}
