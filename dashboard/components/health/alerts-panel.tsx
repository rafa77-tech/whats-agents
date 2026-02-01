'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertTriangle, AlertCircle, Info, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import Link from 'next/link'
import {
  getAlertSeverityColors,
  getAlertSeverityLabel,
  sortAlertsBySeverity,
  countAlertsBySeverity,
  MAX_DISPLAYED_ALERTS,
} from '@/lib/health'
import type { HealthAlert, AlertSeverity } from '@/lib/health'

interface AlertsPanelProps {
  alerts: HealthAlert[]
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  const counts = countAlertsBySeverity(alerts)
  const criticalCount = counts.critical
  const warnCount = counts.warn
  const infoCount = counts.info

  const getSeverityIcon = (severity: AlertSeverity) => {
    const colors = getAlertSeverityColors(severity)
    switch (severity) {
      case 'critical':
        return <AlertTriangle className={`h-4 w-4 ${colors.icon}`} />
      case 'warn':
        return <AlertCircle className={`h-4 w-4 ${colors.icon}`} />
      default:
        return <Info className={`h-4 w-4 ${colors.icon}`} />
    }
  }

  const getSeverityBadge = (severity: AlertSeverity) => {
    const colors = getAlertSeverityColors(severity)
    return <Badge className={colors.badge}>{getAlertSeverityLabel(severity)}</Badge>
  }

  const sortedAlerts = sortAlertsBySeverity(alerts)

  return (
    <Card className={cn(criticalCount > 0 && 'border-red-200')}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle
              className={cn('h-5 w-5', criticalCount > 0 ? 'text-red-500' : 'text-yellow-500')}
            />
            Alertas Ativos: {alerts.length}
          </CardTitle>
          <div className="flex gap-2">
            {criticalCount > 0 && (
              <Badge variant="outline" className="border-red-200 text-red-600">
                {criticalCount} critico{criticalCount > 1 ? 's' : ''}
              </Badge>
            )}
            {warnCount > 0 && (
              <Badge variant="outline" className="border-yellow-200 text-yellow-600">
                {warnCount} alerta{warnCount > 1 ? 's' : ''}
              </Badge>
            )}
            {infoCount > 0 && (
              <Badge variant="outline" className="border-blue-200 text-blue-600">
                {infoCount} info
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {sortedAlerts.slice(0, MAX_DISPLAYED_ALERTS).map((alert) => {
            const colors = getAlertSeverityColors(alert.severity)
            return (
              <div
                key={alert.id}
                className={cn(
                  'flex items-center justify-between rounded-lg border p-3',
                  colors.border,
                  colors.bg
                )}
              >
                <div className="flex items-center gap-3">
                  {getSeverityIcon(alert.severity)}
                  <div>
                    <p className="text-sm font-medium">{alert.message}</p>
                    <p className="text-xs text-gray-500">Fonte: {alert.source}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getSeverityBadge(alert.severity)}
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/monitor">
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            )
          })}
          {alerts.length > MAX_DISPLAYED_ALERTS && (
            <p className="text-center text-sm text-gray-500">
              + {alerts.length - MAX_DISPLAYED_ALERTS} alerta
              {alerts.length - MAX_DISPLAYED_ALERTS > 1 ? 's' : ''} adicional
              {alerts.length - MAX_DISPLAYED_ALERTS > 1 ? 'is' : ''}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
