/**
 * Chips Page - Sprint 45
 *
 * Pagina principal do modulo de gerenciamento de chips.
 * Consolidada em uma unica pagina com tabs.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { ChipsUnifiedPage } from '@/components/chips/chips-unified-page'
import { ChipsPageSkeleton } from '@/components/chips/chips-page-skeleton'

export const metadata: Metadata = {
  title: 'Chips | Julia Dashboard',
  description: 'Gerenciamento do pool de chips WhatsApp',
}

export default function ChipsPage() {
  return (
    <Suspense fallback={<ChipsPageSkeleton />}>
      <ChipsUnifiedPage />
    </Suspense>
  )
}
