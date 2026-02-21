import { Suspense } from 'react'
import { Metadata } from 'next'
import { MetaUnifiedPage } from '@/components/meta/meta-unified-page'
import { MetaPageSkeleton } from '@/components/meta/meta-page-skeleton'

export const metadata: Metadata = {
  title: 'Meta | Julia Dashboard',
  description: 'Gestao Meta WhatsApp Cloud API',
}

export default function MetaPage() {
  return (
    <Suspense fallback={<MetaPageSkeleton />}>
      <MetaUnifiedPage />
    </Suspense>
  )
}
