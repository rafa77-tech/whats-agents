'use client'

import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  Settings,
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
  { name: 'Chips', href: '/chips', icon: Smartphone },
  { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
  { name: 'Sistema', href: '/sistema', icon: Settings },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <div className="safe-area-pb border-t border-gray-200 bg-white px-2 py-2">
      <nav className="flex items-center justify-around">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.name}
              href={item.href as Route}
              className={cn(
                'flex min-w-[64px] flex-col items-center gap-1 rounded-lg px-3 py-2 transition-colors',
                isActive ? 'text-revoluna-400' : 'text-gray-500'
              )}
            >
              <item.icon className="h-6 w-6" />
              <span className="text-xs font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
