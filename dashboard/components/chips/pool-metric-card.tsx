/**
 * Pool Metric Card - Sprint 36
 *
 * Card para exibir métricas agregadas do pool.
 */

'use client'

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface PoolMetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: ReactNode
  trend?: {
    direction: 'up' | 'down' | 'stable'
    value: number
    label?: string
  }
  status?: 'success' | 'warning' | 'danger' | 'neutral'
}

const statusStyles = {
  success: 'border-l-4 border-l-green-500',
  warning: 'border-l-4 border-l-yellow-500',
  danger: 'border-l-4 border-l-red-500',
  neutral: 'border-l-4 border-l-gray-300',
}

export function PoolMetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  status = 'neutral',
}: PoolMetricCardProps) {
  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white p-5', statusStyles[status])}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
          {trend && (
            <div
              className={cn(
                'mt-2 flex items-center gap-1 text-sm',
                trend.direction === 'up'
                  ? 'text-green-600'
                  : trend.direction === 'down'
                    ? 'text-red-600'
                    : 'text-gray-500'
              )}
            >
              {trend.direction === 'up' && <TrendingUp className="h-4 w-4" />}
              {trend.direction === 'down' && <TrendingDown className="h-4 w-4" />}
              {trend.direction === 'stable' && <Minus className="h-4 w-4" />}
              <span>
                {trend.direction === 'up' ? '+' : trend.direction === 'down' ? '-' : ''}
                {Math.abs(trend.value)}%
              </span>
              {trend.label && <span className="text-gray-400">{trend.label}</span>}
            </div>
          )}
        </div>
        <div className="text-gray-400">{icon}</div>
      </div>
    </div>
  )
}
