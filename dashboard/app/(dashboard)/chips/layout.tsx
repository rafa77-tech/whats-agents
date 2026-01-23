/**
 * Chips Module Layout - Sprint 36
 *
 * Layout compartilhado para todas as páginas do módulo de chips.
 */

import { ReactNode } from 'react'
import { ChipsModuleSidebar } from '@/components/chips/chips-module-sidebar'
import { ChipsMobileNav } from '@/components/chips/chips-mobile-nav'

interface ChipsLayoutProps {
  children: ReactNode
}

export default function ChipsLayout({ children }: ChipsLayoutProps) {
  return (
    <div className="flex min-h-screen">
      <ChipsMobileNav />
      <ChipsModuleSidebar />
      <main className="flex-1 overflow-auto pt-14 lg:pt-0">{children}</main>
    </div>
  )
}
