/**
 * Scheduler Page - Sprint 36
 *
 * Página do scheduler de atividades de warmup.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { SchedulerPageContent } from '@/components/chips/scheduler-page-content'

export const metadata: Metadata = {
  title: 'Scheduler | Chips | Julia Dashboard',
  description: 'Scheduler de atividades de warmup dos chips',
}

function SchedulerSkeleton() {
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

export default function SchedulerPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1400px] p-6">
        <Suspense fallback={<SchedulerSkeleton />}>
          <SchedulerPageContent />
        </Suspense>
      </div>
    </div>
  )
}
