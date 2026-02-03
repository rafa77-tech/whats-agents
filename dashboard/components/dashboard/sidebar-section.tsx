/**
 * SidebarSection - Sprint 45
 *
 * Componente de label de secao para agrupar itens na sidebar.
 * Parte da reorganizacao da arquitetura de informacao.
 */

'use client'

import { cn } from '@/lib/utils'

interface SidebarSectionProps {
  label: string
  children: React.ReactNode
  className?: string
}

export function SidebarSection({ label, children, className }: SidebarSectionProps) {
  return (
    <div className={cn('mt-6 first:mt-0', className)}>
      <h3 className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-foreground/60">
        {label}
      </h3>
      <div className="space-y-0.5">{children}</div>
    </div>
  )
}
