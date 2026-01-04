'use client'

import { useState } from 'react'
import { Menu, Search, X } from 'lucide-react'
import { Sidebar } from './sidebar'
import { JuliaStatus } from './julia-status'
import { NotificationBell } from './notification-bell'
import { UserMenu } from './user-menu'

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-4 px-4 py-3 lg:px-6">
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="-ml-2 rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 lg:hidden"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Abrir menu</span>
          </button>

          {/* Mobile logo */}
          <div className="flex items-center gap-2 lg:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-revoluna-400">
              <span className="text-sm font-bold text-white">J</span>
            </div>
            <span className="font-semibold text-gray-900">Julia</span>
          </div>

          {/* Julia Status - hidden on mobile */}
          <div className="hidden sm:flex">
            <JuliaStatus />
          </div>

          {/* Search - Desktop only */}
          <div className="hidden max-w-md flex-1 md:flex">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="search"
                placeholder="Buscar medicos, conversas..."
                className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-4 text-sm outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-revoluna-400"
              />
            </div>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Right side actions */}
          <div className="flex items-center gap-1">
            {/* Notifications */}
            <NotificationBell />

            {/* User Menu */}
            <UserMenu />
          </div>
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          />

          {/* Sidebar drawer */}
          <div className="fixed inset-y-0 left-0 w-72 bg-white shadow-xl">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute right-4 top-4 z-10 rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Fechar menu</span>
            </button>
            <Sidebar onNavigate={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      )}
    </>
  )
}
