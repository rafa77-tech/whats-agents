/**
 * Alerts List Component - Sprint 33 E13
 *
 * Card showing recent alerts sorted by severity with auto-refresh.
 * Uses CRITICAL priority (15s) for quick alert updates.
 */

'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertItem } from './alert-item'
import { type AlertsData } from '@/types/dashboard'
import { Bell, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { REFRESH_INTERVALS } from '@/lib/config'

interface AlertsListProps {
  initialData?: AlertsData
  autoRefresh?: boolean
  refreshInterval?: number // em ms, defaults to CRITICAL priority
}

export function AlertsList({
  initialData,
  autoRefresh = true,
  refreshInterval = REFRESH_INTERVALS.CRITICAL,
}: AlertsListProps) {
  const [data, setData] = useState<AlertsData | null>(initialData ?? null)
  const [loading, setLoading] = useState(!initialData)

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/alerts')
      const json = (await res.json()) as AlertsData
      if (res.ok) {
        setData(json)
      }
    } catch (error) {
      console.error('Error fetching alerts:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!initialData) {
      void fetchAlerts()
    }

    if (autoRefresh) {
      const interval = setInterval(() => {
        void fetchAlerts()
      }, refreshInterval)
      return () => clearInterval(interval)
    }
    return undefined
  }, [initialData, autoRefresh, refreshInterval, fetchAlerts])

  // Ordenar alertas: critico > warning > info
  const sortedAlerts = data?.alerts
    ? [...data.alerts].sort((a, b) => {
        const order = { critical: 0, warning: 1, info: 2 }
        return order[a.severity] - order[b.severity]
      })
    : []

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Bell className="h-4 w-4" />
            Alertas
          </CardTitle>
          {data && data.totalCritical > 0 && (
            <Badge variant="destructive" className="text-xs">
              {data.totalCritical} critico{data.totalCritical > 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/70" />
          </div>
        ) : sortedAlerts.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            <Bell className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
            <p>Nenhum alerta no momento</p>
          </div>
        ) : (
          sortedAlerts.map((alert) => <AlertItem key={alert.id} alert={alert} />)
        )}
      </CardContent>
    </Card>
  )
}
