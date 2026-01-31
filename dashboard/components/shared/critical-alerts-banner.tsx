'use client'

import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, X, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

interface CriticalAlert {
  id: string
  message: string
  source: string
}

export function CriticalAlertsBanner() {
  const [alerts, setAlerts] = useState<CriticalAlert[]>([])
  const [dismissed, setDismissed] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/alerts')
      if (res.ok) {
        const data = await res.json()
        // Filter for critical alerts only
        const criticalAlerts: CriticalAlert[] = []

        // Check for critical alerts from various sources
        if (data.criticalStale?.length > 0) {
          data.criticalStale.forEach((job: string) => {
            criticalAlerts.push({
              id: `stale-${job}`,
              message: `Job ${job} esta stale (excedeu SLA)`,
              source: 'scheduler',
            })
          })
        }

        // Check for circuit breakers in OPEN state
        if (data.circuits?.some((c: { state: string }) => c.state === 'OPEN')) {
          const openCircuits = data.circuits.filter(
            (c: { state: string }) => c.state === 'OPEN'
          )
          openCircuits.forEach((c: { name: string }) => {
            criticalAlerts.push({
              id: `circuit-${c.name}`,
              message: `Circuit breaker ${c.name} em estado OPEN`,
              source: 'guardrails',
            })
          })
        }

        // Check for high rate limit usage
        if (data.rateLimit) {
          const hourlyPercent = (data.rateLimit.used_hour / data.rateLimit.limit_hour) * 100
          const dailyPercent = (data.rateLimit.used_day / data.rateLimit.limit_day) * 100

          if (hourlyPercent >= 95 || dailyPercent >= 95) {
            criticalAlerts.push({
              id: 'rate-limit',
              message: `Rate limit atingiu ${Math.max(hourlyPercent, dailyPercent).toFixed(0)}%`,
              source: 'rate-limit',
            })
          }
        }

        setAlerts(criticalAlerts)
      }
    } catch {
      // Ignore errors
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAlerts()
    // Poll every 30 seconds
    const interval = setInterval(fetchAlerts, 30000)
    return () => clearInterval(interval)
  }, [fetchAlerts])

  // Auto-show again after 5 minutes if dismissed
  useEffect(() => {
    if (dismissed) {
      const timeout = setTimeout(() => setDismissed(false), 5 * 60 * 1000)
      return () => clearTimeout(timeout)
    }
    return undefined
  }, [dismissed])

  if (loading || dismissed || alerts.length === 0) {
    return null
  }

  return (
    <div className="mb-6 rounded-lg border border-red-300 bg-red-50 p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <div>
            <h3 className="font-medium text-red-800">
              ALERTAS CRITICOS ({alerts.length})
            </h3>
            <ul className="mt-2 space-y-1">
              {alerts.slice(0, 3).map((alert) => (
                <li key={alert.id} className="text-sm text-red-700">
                  • {alert.message}
                </li>
              ))}
              {alerts.length > 3 && (
                <li className="text-sm text-red-600">
                  + {alerts.length - 3} mais alertas
                </li>
              )}
            </ul>
            <Link
              href="/health"
              className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-red-700 hover:text-red-800"
            >
              Ver detalhes no Health Center
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-red-600 hover:text-red-800"
          onClick={() => setDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
