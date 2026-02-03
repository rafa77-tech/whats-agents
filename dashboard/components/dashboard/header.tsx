/**
 * Header - Sprint 45
 *
 * Cabecalho do dashboard com busca global (Command Palette).
 * Atualizado com identidade visual Jull.ia.
 */

'use client'

import { useState } from 'react'
import { Bell, Menu, Search, X } from 'lucide-react'
import { Sidebar } from './sidebar'
import { useCommandPalette } from '@/components/command-palette'

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { setOpen: openCommandPalette } = useCommandPalette()

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between px-4 py-3 lg:px-6">
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="-ml-2 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:hidden"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Search button - abre Command Palette */}
          <div className="mx-4 max-w-lg flex-1 lg:mx-0">
            <button
              onClick={() => openCommandPalette(true)}
              className="flex w-full items-center gap-3 rounded-xl border border-border bg-muted/50 px-4 py-2.5 text-sm text-muted-foreground transition-all hover:border-primary/30 hover:bg-muted"
            >
              <Search className="h-4 w-4" />
              <span className="flex-1 text-left">Buscar...</span>
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded-md border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
                <span className="text-xs">⌘</span>K
              </kbd>
            </button>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-1">
            {/* Notifications */}
            <button
              className="relative rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Notificacoes"
            >
              <Bell className="h-5 w-5" />
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary" />
            </button>

            {/* User avatar */}
            <button className="bg-jullia-gradient ml-1 flex h-8 w-8 items-center justify-center rounded-full transition-transform hover:scale-105">
              <span className="text-xs font-semibold text-white">R</span>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Sidebar */}
          <div className="sidebar-bg-white fixed inset-y-0 left-0 w-64 shadow-xl">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute right-3 top-3 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Fechar menu"
            >
              <X className="h-5 w-5" />
            </button>
            <Sidebar />
          </div>
        </div>
      )}
    </>
  )
}
