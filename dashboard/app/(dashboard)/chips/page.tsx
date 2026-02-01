/**
 * Chips Page - Sprint 36
 *
 * Página principal do módulo de gerenciamento de chips.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { ChipsPageContent } from '@/components/chips/chips-page-content'
import { ChipsPageSkeleton } from '@/components/chips/chips-page-skeleton'

export const metadata: Metadata = {
  title: 'Chips | Julia Dashboard',
  description: 'Gerenciamento do pool de chips WhatsApp',
}

export default function ChipsPage() {
  return (
    <div className="min-h-screen bg-secondary">
      <div className="mx-auto max-w-[1600px] p-6">
        <Suspense fallback={<ChipsPageSkeleton />}>
          <ChipsPageContent />
        </Suspense>
      </div>
    </div>
  )
}
