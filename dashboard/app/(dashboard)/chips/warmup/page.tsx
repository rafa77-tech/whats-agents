/**
 * Warmup Page - Sprint 42
 *
 * Página de atividades de warmup dos chips.
 * Renomeado de /chips/scheduler para /chips/warmup.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { WarmupPageContent } from '@/components/chips/warmup-page-content'

export const metadata: Metadata = {
  title: 'Warmup | Chips | Julia Dashboard',
  description: 'Atividades de warmup dos chips',
}

function WarmupSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-gray-200" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded bg-gray-200" />
        ))}
      </div>
      <div className="h-96 rounded bg-gray-200" />
    </div>
  )
}

export default function WarmupPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1400px] p-6">
        <Suspense fallback={<WarmupSkeleton />}>
          <WarmupPageContent />
        </Suspense>
      </div>
    </div>
  )
}
