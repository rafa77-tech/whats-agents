/**
 * Chip Metrics Cards - Sprint 36
 *
 * Cards de métricas do chip.
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChipMetrics } from '@/types/chips'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface ChipMetricsCardsProps {
  metrics: ChipMetrics
}

interface MetricItem {
  label: string
  value: number | string
  previousValue?: number
  format?: 'number' | 'percent' | 'time'
  inverse?: boolean // true if lower is better (e.g., errors)
}

export function ChipMetricsCards({ metrics }: ChipMetricsCardsProps) {
  const metricItems: MetricItem[] = [
    {
      label: 'Mensagens Enviadas',
      value: metrics.messagesSent,
      previousValue: metrics.previousMessagesSent,
      format: 'number',
    },
    {
      label: 'Taxa de Resposta',
      value: metrics.responseRate,
      previousValue: metrics.previousResponseRate,
      format: 'percent',
    },
    {
      label: 'Taxa de Entrega',
      value: metrics.deliveryRate,
      format: 'percent',
    },
    {
      label: 'Erros',
      value: metrics.errorCount,
      previousValue: metrics.previousErrorCount,
      format: 'number',
      inverse: true,
    },
    {
      label: 'Mensagens Recebidas',
      value: metrics.messagesReceived,
      format: 'number',
    },
    {
      label: 'Tempo Médio de Resposta',
      value: metrics.avgResponseTime,
      format: 'time',
    },
  ]

  const formatValue = (value: number, format?: string) => {
    switch (format) {
      case 'percent':
        return `${value.toFixed(1)}%`
      case 'time':
        if (value < 60) return `${value.toFixed(0)}s`
        return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`
      default:
        return value.toLocaleString()
    }
  }

  const calculateTrend = (
    current: number,
    previous: number | undefined,
    inverse?: boolean
  ): {
    direction: 'up' | 'down' | 'neutral'
    value: number
    isPositive: boolean
  } => {
    if (previous === undefined || previous === 0)
      return { direction: 'neutral', value: 0, isPositive: true }

    const diff = ((current - previous) / previous) * 100
    const direction: 'up' | 'down' | 'neutral' = diff > 5 ? 'up' : diff < -5 ? 'down' : 'neutral'

    // If inverse is true, up is bad and down is good
    const isPositive = inverse ? direction === 'down' : direction === 'up'

    return { direction, value: Math.abs(diff), isPositive }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>Métricas ({metrics.period})</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {metricItems.map((item) => {
            const trend = calculateTrend(
              typeof item.value === 'number' ? item.value : 0,
              item.previousValue,
              item.inverse
            )

            return (
              <div key={item.label} className="rounded-lg bg-muted/50 p-3">
                <div className="mb-1 text-sm text-muted-foreground">{item.label}</div>
                <div className="flex items-center justify-between">
                  <span className="text-xl font-semibold">
                    {formatValue(typeof item.value === 'number' ? item.value : 0, item.format)}
                  </span>
                  {trend.direction !== 'neutral' && item.previousValue !== undefined && (
                    <TrendIndicator
                      direction={trend.direction as 'up' | 'down'}
                      value={trend.value}
                      isPositive={trend.isPositive}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

function TrendIndicator({
  direction,
  value,
  isPositive,
}: {
  direction: 'up' | 'down'
  value: number
  isPositive: boolean
}) {
  const Icon = direction === 'up' ? TrendingUp : TrendingDown
  const colorClass = isPositive ? 'text-status-success-solid' : 'text-status-error-solid'

  return (
    <div className={cn('flex items-center gap-1 text-sm', colorClass)}>
      <Icon className="h-4 w-4" />
      <span>{value.toFixed(0)}%</span>
    </div>
  )
}
