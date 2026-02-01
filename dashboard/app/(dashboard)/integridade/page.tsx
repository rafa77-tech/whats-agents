/**
 * Integridade Page - Sprint 43
 *
 * Pagina de integridade de dados: KPIs, anomalias, violacoes, auditoria.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { IntegridadePageContent } from '@/components/integridade/integridade-page-content'

export const metadata: Metadata = {
  title: 'Integridade | Julia Dashboard',
  description: 'Monitoramento de integridade e anomalias do sistema',
}

function IntegridadeSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-muted" />
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 rounded bg-muted" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="h-24 rounded bg-muted" />
        <div className="h-24 rounded bg-muted" />
      </div>
      <div className="h-96 rounded bg-muted" />
    </div>
  )
}

export default function IntegridadePage() {
  return (
    <div className="min-h-screen bg-secondary">
      <div className="mx-auto max-w-[1600px] p-6">
        <Suspense fallback={<IntegridadeSkeleton />}>
          <IntegridadePageContent />
        </Suspense>
      </div>
    </div>
  )
}
