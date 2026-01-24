'use client'

import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  Building2,
  Settings,
  HelpCircle,
  Power,
  Smartphone,
  type LucideIcon,
} from 'lucide-react'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Pool de Chips', href: '/chips', icon: Smartphone },
  { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
  { name: 'Hospitais Bloqueados', href: '/hospitais/bloqueados', icon: Building2 },
  { name: 'Sistema', href: '/sistema', icon: Settings },
  { name: 'Ajuda', href: '/ajuda', icon: HelpCircle },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-gray-200 px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-revoluna-400">
          <span className="text-lg font-bold text-white">J</span>
        </div>
        <div>
          <h1 className="font-bold text-gray-900">Julia</h1>
          <p className="text-xs text-gray-500">Dashboard</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.name}
              href={item.href as Route}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-revoluna-50 text-revoluna-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              )}
            >
              <item.icon
                className={cn('h-5 w-5', isActive ? 'text-revoluna-400' : 'text-gray-400')}
              />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 p-4">
        <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100">
          <Power className="h-5 w-5 text-gray-400" />
          Sair
        </button>
      </div>
    </div>
  )
}
