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
  success: 'border-l-4 border-l-status-success-solid',
  warning: 'border-l-4 border-l-status-warning-solid',
  danger: 'border-l-4 border-l-status-error-solid',
  neutral: 'border-l-4 border-l-border',
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
    <div className={cn('rounded-lg border border-border bg-card p-5', statusStyles[status])}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-muted-foreground/70">{subtitle}</p>}
          {trend && (
            <div
              className={cn(
                'mt-2 flex items-center gap-1 text-sm',
                trend.direction === 'up'
                  ? 'text-status-success-foreground'
                  : trend.direction === 'down'
                    ? 'text-status-error-foreground'
                    : 'text-muted-foreground'
              )}
            >
              {trend.direction === 'up' && <TrendingUp className="h-4 w-4" />}
              {trend.direction === 'down' && <TrendingDown className="h-4 w-4" />}
              {trend.direction === 'stable' && <Minus className="h-4 w-4" />}
              <span>
                {trend.direction === 'up' ? '+' : trend.direction === 'down' ? '-' : ''}
                {Math.abs(trend.value).toFixed(1)}%
              </span>
              {trend.label && <span className="text-muted-foreground/70">{trend.label}</span>}
            </div>
          )}
        </div>
        <div className="text-muted-foreground">{icon}</div>
      </div>
    </div>
  )
}
