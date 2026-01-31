/**
 * Monitor Page - Sprint 42
 *
 * Pagina de monitoramento de jobs e saude do sistema.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { MonitorPageContent } from '@/components/monitor/monitor-page-content'

export const metadata: Metadata = {
  title: 'Monitor | Julia Dashboard',
  description: 'Monitoramento de jobs e saude do sistema',
}

function MonitorSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-gray-200" />
      <div className="h-32 rounded bg-gray-200" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded bg-gray-200" />
        ))}
      </div>
      <div className="h-12 rounded bg-gray-200" />
      <div className="h-96 rounded bg-gray-200" />
    </div>
  )
}

export default function MonitorPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1600px] p-6">
        <Suspense fallback={<MonitorSkeleton />}>
          <MonitorPageContent />
        </Suspense>
      </div>
    </div>
  )
}
