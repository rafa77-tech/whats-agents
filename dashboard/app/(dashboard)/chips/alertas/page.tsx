/**
 * Chips Alerts Page - Sprint 36
 *
 * Página de alertas do módulo de chips.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { AlertsPageContent } from '@/components/chips/alerts-page-content'
import { AlertsPageSkeleton } from '@/components/chips/alerts-page-skeleton'

export const metadata: Metadata = {
  title: 'Alertas | Chips | Julia Dashboard',
  description: 'Alertas do pool de chips WhatsApp',
}

export default function AlertsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1400px] p-6">
        <Suspense fallback={<AlertsPageSkeleton />}>
          <AlertsPageContent />
        </Suspense>
      </div>
    </div>
  )
}
