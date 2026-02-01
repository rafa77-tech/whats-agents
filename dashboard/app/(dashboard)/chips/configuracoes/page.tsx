/**
 * Chips Config Page - Sprint 36
 *
 * Página de configurações do pool de chips.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { ConfigPageContent } from '@/components/chips/config-page-content'

export const metadata: Metadata = {
  title: 'Configurações | Chips | Julia Dashboard',
  description: 'Configurações do pool de chips WhatsApp',
}

function ConfigSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-muted" />
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 rounded bg-muted" />
        ))}
      </div>
    </div>
  )
}

export default function ConfigPage() {
  return (
    <div className="min-h-screen bg-secondary">
      <div className="mx-auto max-w-[1000px] p-6">
        <Suspense fallback={<ConfigSkeleton />}>
          <ConfigPageContent />
        </Suspense>
      </div>
    </div>
  )
}
