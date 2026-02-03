/**
 * Chips Module Layout - Sprint 45
 *
 * Layout do modulo de chips.
 * Usa o layout padrao do dashboard (com sidebar).
 */

import { ReactNode } from 'react'

interface ChipsLayoutProps {
  children: ReactNode
}

export default function ChipsLayout({ children }: ChipsLayoutProps) {
  return <div className="mx-auto max-w-[1600px]">{children}</div>
}
