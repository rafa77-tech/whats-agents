'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { LayoutDashboard, MessageSquare, Users, Briefcase, MoreHorizontal } from 'lucide-react'

const navigation = [
  { name: 'Home', href: '/', icon: LayoutDashboard },
  { name: 'Conversas', href: '/conversas', icon: MessageSquare },
  { name: 'Medicos', href: '/medicos', icon: Users },
  { name: 'Vagas', href: '/vagas', icon: Briefcase },
  { name: 'Mais', href: '/sistema', icon: MoreHorizontal },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <div className="safe-area-pb border-t border-gray-200 bg-white px-2 py-2">
      <nav className="flex items-center justify-around">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
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
