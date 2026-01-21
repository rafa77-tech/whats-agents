/**
 * Activity Feed Component - Sprint 33 E14
 *
 * Timeline of recent system events with auto-refresh.
 * Uses NORMAL priority (60s) as this is informational data.
 */

'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ActivityItem } from './activity-item'
import { type ActivityFeedData } from '@/types/dashboard'
import { Activity, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { REFRESH_INTERVALS } from '@/lib/config'

interface ActivityFeedProps {
  initialData?: ActivityFeedData
  autoRefresh?: boolean
  refreshInterval?: number // defaults to NORMAL priority
  limit?: number
}

export function ActivityFeed({
  initialData,
  autoRefresh = true,
  refreshInterval = REFRESH_INTERVALS.NORMAL,
  limit = 10,
}: ActivityFeedProps) {
  const [data, setData] = useState<ActivityFeedData | null>(initialData ?? null)
  const [loading, setLoading] = useState(!initialData)

  const fetchActivity = useCallback(async () => {
    try {
      const res = await fetch(`/api/dashboard/activity?limit=${limit}`)
      const json = (await res.json()) as ActivityFeedData
      if (res.ok) {
        setData(json)
      }
    } catch (error) {
      console.error('Error fetching activity:', error)
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => {
    if (!initialData) {
      void fetchActivity()
    }

    if (autoRefresh) {
      const interval = setInterval(() => {
        void fetchActivity()
      }, refreshInterval)
      return () => clearInterval(interval)
    }
    return undefined
  }, [initialData, autoRefresh, refreshInterval, fetchActivity])

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-gray-500">
          <Activity className="h-4 w-4" />
          Atividade Recente
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : data?.events.length === 0 ? (
          <div className="py-8 text-center text-gray-500">
            <Activity className="mx-auto mb-2 h-8 w-8 text-gray-300" />
            <p>Nenhuma atividade recente</p>
          </div>
        ) : (
          <div className="divide-y">
            {data?.events.map((event) => (
              <ActivityItem key={event.id} event={event} />
            ))}
          </div>
        )}

        {data?.hasMore && (
          <div className="mt-4 border-t pt-4">
            <Button variant="ghost" size="sm" className="w-full">
              Ver mais
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
