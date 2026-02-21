'use client'

import { Skeleton } from '@/components/ui/skeleton'

export function MetaPageSkeleton() {
  return (
    <div className="min-h-screen bg-secondary">
      <div className="mx-auto max-w-[1600px] p-6">
        {/* Tab bar skeleton */}
        <Skeleton className="mb-6 h-10 w-full max-w-md" />

        {/* Cards row */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>

        {/* Table skeleton */}
        <Skeleton className="h-96 rounded-xl" />
      </div>
    </div>
  )
}
