/**
 * Health Center Page - Sprint 43
 *
 * Pagina consolidada de saude do sistema: score, alertas, circuits, rate limit, fila, jobs.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { HealthPageContent } from '@/components/health/health-page-content'

export const metadata: Metadata = {
  title: 'Health Center | Julia Dashboard',
  description: 'Centro de saude e monitoramento do sistema',
}

function HealthSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-gray-200" />
      <div className="flex justify-center">
        <div className="h-40 w-40 rounded-full bg-gray-200" />
      </div>
      <div className="grid grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 rounded bg-gray-200" />
        ))}
      </div>
      <div className="h-48 rounded bg-gray-200" />
      <div className="grid grid-cols-2 gap-4">
        <div className="h-64 rounded bg-gray-200" />
        <div className="h-64 rounded bg-gray-200" />
      </div>
    </div>
  )
}

export default function HealthPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1600px] p-6">
        <Suspense fallback={<HealthSkeleton />}>
          <HealthPageContent />
        </Suspense>
      </div>
    </div>
  )
}
