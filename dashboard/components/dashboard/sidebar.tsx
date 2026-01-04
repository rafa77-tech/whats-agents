'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/use-auth'
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Briefcase,
  Megaphone,
  BarChart3,
  Settings,
  Shield,
  Power,
  Loader2,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Conversas', href: '/conversas', icon: MessageSquare },
  { name: 'Medicos', href: '/medicos', icon: Users },
  { name: 'Vagas', href: '/vagas', icon: Briefcase },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Metricas', href: '/metricas', icon: BarChart3 },
  { name: 'Sistema', href: '/sistema', icon: Settings },
  { name: 'Auditoria', href: '/auditoria', icon: Shield, requiredRole: 'admin' as const },
]

const ROLE_LABELS: Record<string, string> = {
  viewer: 'Visualizador',
  operator: 'Operador',
  manager: 'Gestor',
  admin: 'Admin',
}

interface SidebarProps {
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps = {}) {
  const pathname = usePathname()
  const { dashboardUser, signOut, loading, hasPermission } = useAuth()

  const handleSignOut = async () => {
    await signOut()
  }

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
          // Check role permission if required
          if (item.requiredRole && !hasPermission(item.requiredRole)) {
            return null
          }

          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={onNavigate}
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

      {/* User info & Logout */}
      <div className="space-y-3 border-t border-gray-200 p-4">
        {/* User info */}
        {dashboardUser && (
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium text-gray-900">{dashboardUser.nome}</p>
            <p className="text-xs text-gray-500">
              {ROLE_LABELS[dashboardUser.role] || dashboardUser.role}
            </p>
          </div>
        )}

        {/* Logout button */}
        <button
          onClick={handleSignOut}
          disabled={loading}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          ) : (
            <Power className="h-5 w-5 text-gray-400" />
          )}
          Sair
        </button>
      </div>
    </div>
  )
}
