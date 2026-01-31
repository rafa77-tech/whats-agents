/**
 * System Health Card - Sprint 42
 *
 * Exibe status geral de saude do sistema com score e breakdown.
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SystemHealthData, SystemHealthStatus } from '@/types/monitor'

interface SystemHealthCardProps {
  data: SystemHealthData | null
  isLoading?: boolean
}

const STATUS_CONFIG: Record<
  SystemHealthStatus,
  {
    label: string
    color: string
    bgColor: string
    icon: typeof CheckCircle
  }
> = {
  healthy: {
    label: 'Saudavel',
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    icon: CheckCircle,
  },
  degraded: {
    label: 'Degradado',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: AlertTriangle,
  },
  critical: {
    label: 'Critico',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    icon: XCircle,
  },
}

export function SystemHealthCard({ data, isLoading }: SystemHealthCardProps) {
  if (isLoading || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-32 rounded bg-gray-200" />
            <div className="h-4 w-full rounded bg-gray-200" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const config = STATUS_CONFIG[data.status]
  const StatusIcon = config.icon

  return (
    <Card
      className={cn('border-l-4', {
        'border-l-green-500': data.status === 'healthy',
        'border-l-yellow-500': data.status === 'degraded',
        'border-l-red-500': data.status === 'critical',
      })}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5" />
            Saude do Sistema
          </CardTitle>
          <Badge className={cn(config.bgColor, config.color)}>
            <StatusIcon className="mr-1 h-3 w-3" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Score principal */}
          <div className="flex items-end gap-2">
            <span className={cn('text-4xl font-bold', config.color)}>{data.score}</span>
            <span className="mb-1 text-gray-500">/ 100</span>
          </div>

          {/* Progress bar */}
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className={cn('h-full transition-all', {
                'bg-green-500': data.score >= 80,
                'bg-yellow-500': data.score >= 50 && data.score < 80,
                'bg-red-500': data.score < 50,
              })}
              style={{ width: `${data.score}%` }}
            />
          </div>

          {/* Breakdown */}
          <div className="grid grid-cols-2 gap-4 pt-2 md:grid-cols-4">
            {Object.entries(data.checks).map(([key, check]) => (
              <div key={key} className="rounded-lg bg-gray-50 p-3">
                <div className="mb-1 text-xs capitalize text-gray-500">{key}</div>
                <div className="flex items-center gap-1">
                  <span className="font-semibold">{check.score}</span>
                  <span className="text-xs text-gray-400">/ {check.max}</span>
                </div>
                <div className="mt-1 truncate text-xs text-gray-400">{check.details}</div>
              </div>
            ))}
          </div>

          {/* Last updated */}
          <div className="text-xs text-gray-400" suppressHydrationWarning>
            Atualizado: {new Date(data.lastUpdated).toLocaleString('pt-BR')}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
