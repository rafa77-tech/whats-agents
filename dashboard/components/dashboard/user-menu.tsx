'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/hooks/use-auth'
import { ChevronDown, LogOut, User, Settings } from 'lucide-react'
import Link from 'next/link'

const ROLE_LABELS: Record<string, string> = {
  viewer: 'Visualizador',
  operator: 'Operador',
  manager: 'Gestor',
  admin: 'Admin',
}

export function UserMenu() {
  const { dashboardUser, signOut, loading } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSignOut = async () => {
    setIsOpen(false)
    await signOut()
  }

  if (loading || !dashboardUser) {
    return (
      <div className="h-9 w-9 rounded-full bg-gray-200 animate-pulse" />
    )
  }

  const initials = dashboardUser.nome
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-1 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div className="h-9 w-9 rounded-full bg-revoluna-100 flex items-center justify-center">
          <span className="text-sm font-medium text-revoluna-700">{initials}</span>
        </div>
        <ChevronDown
          className={`hidden sm:block h-4 w-4 text-gray-500 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 rounded-lg bg-white shadow-lg border border-gray-200 py-1 z-50">
          {/* User info */}
          <div className="px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-900 truncate">
              {dashboardUser.nome}
            </p>
            <p className="text-xs text-gray-500">{dashboardUser.email}</p>
            <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded-full bg-revoluna-100 text-revoluna-700">
              {ROLE_LABELS[dashboardUser.role] || dashboardUser.role}
            </span>
          </div>

          {/* Menu items */}
          <div className="py-1">
            <Link
              href="/perfil"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <User className="h-4 w-4" />
              Meu Perfil
            </Link>
            <Link
              href="/sistema"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <Settings className="h-4 w-4" />
              Configuracoes
            </Link>
          </div>

          {/* Logout */}
          <div className="border-t border-gray-100 py-1">
            <button
              onClick={handleSignOut}
              className="flex items-center gap-3 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
