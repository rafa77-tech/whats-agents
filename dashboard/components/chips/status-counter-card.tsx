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

const statusConfig: Record<ChipStatus, { label: string; color: string; bgColor: string }> = {
  active: { label: 'Ativos', color: 'text-green-700', bgColor: 'bg-green-50' },
  ready: { label: 'Prontos', color: 'text-blue-700', bgColor: 'bg-blue-50' },
  warming: { label: 'Aquecendo', color: 'text-yellow-700', bgColor: 'bg-yellow-50' },
  degraded: { label: 'Degradados', color: 'text-orange-700', bgColor: 'bg-orange-50' },
  paused: { label: 'Pausados', color: 'text-gray-700', bgColor: 'bg-gray-50' },
  banned: { label: 'Banidos', color: 'text-red-700', bgColor: 'bg-red-50' },
  provisioned: { label: 'Provisionados', color: 'text-purple-700', bgColor: 'bg-purple-50' },
  pending: { label: 'Pendentes', color: 'text-gray-700', bgColor: 'bg-gray-50' },
  cancelled: { label: 'Cancelados', color: 'text-gray-500', bgColor: 'bg-gray-100' },
  offline: { label: 'Offline', color: 'text-red-700', bgColor: 'bg-red-50' },
}

export function StatusCounterCard({
  status,
  count,
  percentage,
  trend,
  trendValue,
}: StatusCounterCardProps) {
  const config = statusConfig[status]

  return (
    <div className={cn('rounded-lg border p-4', config.bgColor)}>
      <div className="flex items-center justify-between">
        <span className={cn('text-sm font-medium', config.color)}>{config.label}</span>
        {percentage !== undefined && (
          <span className="text-xs text-gray-500">{percentage.toFixed(1)}%</span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={cn('text-3xl font-bold', config.color)}>{count}</span>
        {trend && trendValue !== undefined && trendValue !== 0 && (
          <span
            className={cn(
              'text-sm',
              trend === 'up'
                ? 'text-green-600'
                : trend === 'down'
                  ? 'text-red-600'
                  : 'text-gray-500'
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
