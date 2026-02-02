/**
 * Status Counter Card - Sprint 36
 *
 * Card para exibir contagem de chips por status.
 */

'use client'

import { cn } from '@/lib/utils'
import { ChipStatus } from '@/types/dashboard'

interface StatusCounterCardProps {
  status: ChipStatus
  count: number
  percentage?: number
  trend?: 'up' | 'down' | 'stable'
  trendValue?: number
}

const statusConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  active: {
    label: 'Ativos',
    color: 'text-status-success-foreground',
    bgColor: 'bg-status-success/10',
  },
  ready: { label: 'Prontos', color: 'text-status-info-foreground', bgColor: 'bg-status-info/10' },
  warming: {
    label: 'Aquecendo',
    color: 'text-status-warning-foreground',
    bgColor: 'bg-status-warning/10',
  },
  degraded: {
    label: 'Degradados',
    color: 'text-status-warning-foreground',
    bgColor: 'bg-status-warning/10',
  },
  paused: { label: 'Pausados', color: 'text-status-neutral-foreground', bgColor: 'bg-muted/50' },
  banned: {
    label: 'Banidos',
    color: 'text-status-error-foreground',
    bgColor: 'bg-status-error/10',
  },
  provisioned: {
    label: 'Provisionados',
    color: 'text-status-info-foreground',
    bgColor: 'bg-status-info/10',
  },
  pending: { label: 'Pendentes', color: 'text-status-neutral-foreground', bgColor: 'bg-muted/50' },
  cancelled: { label: 'Cancelados', color: 'text-muted-foreground', bgColor: 'bg-muted' },
  offline: {
    label: 'Offline',
    color: 'text-status-error-foreground',
    bgColor: 'bg-status-error/10',
  },
}

const defaultConfig = {
  label: 'Desconhecido',
  color: 'text-status-neutral-foreground',
  bgColor: 'bg-muted/50',
}

export function StatusCounterCard({
  status,
  count,
  percentage,
  trend,
  trendValue,
}: StatusCounterCardProps) {
  const config = statusConfig[status] || defaultConfig

  return (
    <div className={cn('rounded-lg border p-4', config.bgColor)}>
      <div className="flex items-center justify-between">
        <span className={cn('text-sm font-medium', config.color)}>{config.label}</span>
        {percentage !== undefined && (
          <span className="text-xs text-muted-foreground">{percentage.toFixed(1)}%</span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={cn('text-3xl font-bold', config.color)}>{count}</span>
        {trend && trendValue !== undefined && trendValue !== 0 && (
          <span
            className={cn(
              'text-sm',
              trend === 'up'
                ? 'text-status-success-foreground'
                : trend === 'down'
                  ? 'text-status-error-foreground'
                  : 'text-muted-foreground'
            )}
          >
            {trend === 'up' ? '+' : trend === 'down' ? '-' : ''}
            {Math.abs(trendValue)}
          </span>
        )}
      </div>
    </div>
  )
}
