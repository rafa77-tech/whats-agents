/**
 * Chip Detail Skeleton - Sprint 36
 *
 * Skeleton de loading para a página de detalhes do chip.
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card'

export function ChipDetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      {/* Header skeleton */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="h-8 w-64 rounded bg-muted" />
          <div className="mt-2 flex items-center gap-2">
            <div className="h-6 w-20 rounded-full bg-muted" />
            <div className="h-6 w-24 rounded-full bg-muted" />
          </div>
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-24 rounded bg-muted" />
          <div className="h-9 w-24 rounded bg-muted" />
        </div>
      </div>

      {/* Info cards grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="mb-2 h-4 w-24 rounded bg-muted" />
              <div className="h-8 w-16 rounded bg-muted" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main content area */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column - larger */}
        <div className="space-y-6 lg:col-span-2">
          {/* Trust chart skeleton */}
          <Card>
            <CardHeader>
              <div className="h-6 w-40 rounded bg-muted" />
            </CardHeader>
            <CardContent>
              <div className="h-64 rounded bg-muted" />
            </CardContent>
          </Card>

          {/* Metrics skeleton */}
          <Card>
            <CardHeader>
              <div className="h-6 w-32 rounded bg-muted" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="rounded bg-muted/50 p-3">
                    <div className="mb-2 h-4 w-20 rounded bg-muted" />
                    <div className="h-6 w-12 rounded bg-muted" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right column - info and actions */}
        <div className="space-y-6">
          {/* Chip info skeleton */}
          <Card>
            <CardHeader>
              <div className="h-6 w-36 rounded bg-muted" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex justify-between">
                  <div className="h-4 w-24 rounded bg-muted" />
                  <div className="h-4 w-32 rounded bg-muted" />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Actions skeleton */}
          <Card>
            <CardHeader>
              <div className="h-6 w-24 rounded bg-muted" />
            </CardHeader>
            <CardContent className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-10 rounded bg-muted" />
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Interactions timeline skeleton */}
      <Card>
        <CardHeader>
          <div className="h-6 w-48 rounded bg-muted" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 rounded bg-muted/50 p-3">
                <div className="h-8 w-8 shrink-0 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 rounded bg-muted" />
                  <div className="h-3 w-1/2 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
