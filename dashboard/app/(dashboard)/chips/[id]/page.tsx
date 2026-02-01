/**
 * Chip Detail Page - Sprint 36
 *
 * Página de detalhes de um chip específico.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { ChipDetailContent } from '@/components/chips/chip-detail-content'
import { ChipDetailSkeleton } from '@/components/chips/chip-detail-skeleton'

interface ChipDetailPageProps {
  params: { id: string }
}

export async function generateMetadata({ params }: ChipDetailPageProps): Promise<Metadata> {
  return {
    title: `Chip ${params.id} | Julia Dashboard`,
    description: 'Detalhes do chip WhatsApp',
  }
}

export default function ChipDetailPage({ params }: ChipDetailPageProps) {
  return (
    <div className="min-h-screen bg-secondary">
      <div className="mx-auto max-w-[1400px] p-6">
        <Suspense fallback={<ChipDetailSkeleton />}>
          <ChipDetailContent chipId={params.id} />
        </Suspense>
      </div>
    </div>
  )
}
