/**
 * Grupos Page
 *
 * Pagina de gestao de entrada em grupos WhatsApp.
 */

import { Suspense } from 'react'
import { GroupEntryPageContent } from '@/components/group-entry/group-entry-page-content'
import { Skeleton } from '@/components/ui/skeleton'

function GroupsPageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-2 h-4 w-64" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-9" />
          <Skeleton className="h-9 w-9" />
        </div>
      </div>
      <Skeleton className="h-20 rounded-lg" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-lg" />
    </div>
  )
}

export default function GruposPage() {
  return (
    <Suspense fallback={<GroupsPageSkeleton />}>
      <GroupEntryPageContent />
    </Suspense>
  )
}
