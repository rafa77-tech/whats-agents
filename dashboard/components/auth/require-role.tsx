'use client'

import { useAuth, UserRole } from '@/hooks/use-auth'
import { ShieldX } from 'lucide-react'

interface RequireRoleProps {
  role: UserRole
  children: React.ReactNode
  fallback?: React.ReactNode
}

export function RequireRole({ role, children, fallback }: RequireRoleProps) {
  const { hasPermission, loading } = useAuth()

  if (loading) {
    return null
  }

  if (!hasPermission(role)) {
    if (fallback) {
      return <>{fallback}</>
    }

    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center gap-3">
          <ShieldX className="h-5 w-5 text-red-600" />
          <div>
            <p className="font-medium text-red-900">Acesso negado</p>
            <p className="text-sm text-red-600">
              Você não tem permissão para acessar este recurso.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
