/**
 * Alerts Page Skeleton - Sprint 36
 *
 * Skeleton de loading para a página de alertas.
 */

import { Card, CardContent } from '@/components/ui/card'

export function AlertsPageSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      {/* Header skeleton */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="h-4 w-32 rounded bg-gray-200" />
          <div className="h-8 w-48 rounded bg-gray-200" />
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-24 rounded bg-gray-200" />
          <div className="h-9 w-24 rounded bg-gray-200" />
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="mb-2 h-4 w-24 rounded bg-gray-200" />
              <div className="h-8 w-16 rounded bg-gray-200" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters skeleton */}
      <div className="flex flex-wrap gap-2">
        <div className="h-10 w-40 rounded bg-gray-200" />
        <div className="h-10 w-40 rounded bg-gray-200" />
        <div className="h-10 w-40 rounded bg-gray-200" />
      </div>

      {/* Alerts list skeleton */}
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex items-start gap-4">
                <div className="h-10 w-10 shrink-0 rounded-full bg-gray-200" />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="h-5 w-48 rounded bg-gray-200" />
                    <div className="h-5 w-20 rounded bg-gray-200" />
                  </div>
                  <div className="h-4 w-3/4 rounded bg-gray-200" />
                  <div className="flex items-center gap-4">
                    <div className="h-4 w-24 rounded bg-gray-200" />
                    <div className="h-4 w-32 rounded bg-gray-200" />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Pagination skeleton */}
      <div className="flex items-center justify-between">
        <div className="h-4 w-32 rounded bg-gray-200" />
        <div className="flex gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 w-8 rounded bg-gray-200" />
          ))}
        </div>
      </div>
    </div>
  )
}
