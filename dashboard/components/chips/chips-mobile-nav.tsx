/**
 * Chips Mobile Navigation - Sprint 36
 *
 * Navegação mobile com drawer/sheet.
 */

'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import type { Route } from 'next'
import { Menu, Cpu, LayoutDashboard, AlertTriangle, Calendar, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

const navItems = [
  { title: 'Visao Geral', href: '/chips', icon: LayoutDashboard, exact: true },
  { title: 'Alertas', href: '/chips/alertas', icon: AlertTriangle },
  { title: 'Scheduler', href: '/chips/scheduler', icon: Calendar },
  { title: 'Configuracoes', href: '/chips/configuracoes', icon: Settings },
]

export function ChipsMobileNav() {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href
    return pathname.startsWith(href)
  }

  return (
    <div className="fixed left-0 right-0 top-0 z-50 border-b border-gray-200 bg-white lg:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-5 w-5 text-blue-600" />
          <span className="font-semibold">Pool de Chips</span>
        </div>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Menu">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <Cpu className="h-5 w-5 text-blue-600" />
                Pool de Chips
              </SheetTitle>
            </SheetHeader>
            <nav className="mt-6 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.href}
                    href={item.href as Route}
                    onClick={() => setOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium',
                      isActive(item.href, item.exact)
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-50'
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.title}
                  </Link>
                )
              })}
            </nav>
            <div className="absolute bottom-4 left-4">
              <Link
                href={'/dashboard' as Route}
                className="text-sm text-gray-500 hover:text-gray-700"
                onClick={() => setOpen(false)}
              >
                ← Voltar ao Dashboard
              </Link>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  )
}
