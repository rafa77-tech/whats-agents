'use client'

import { type ChipPoolAggregatedMetrics } from '@/types/dashboard'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface ChipPoolMetricsProps {
  metrics: ChipPoolAggregatedMetrics
}

function MetricItem({
  label,
  value,
  previousValue,
  format,
  invertTrend = false,
}: {
  label: string
  value: number
  previousValue: number
  format: 'number' | 'percent'
  invertTrend?: boolean
}) {
  const diff = previousValue !== 0 ? ((value - previousValue) / previousValue) * 100 : 0
  const isPositive = diff > 0
  // Para taxa block e erros, queda e bom
  const isGood = invertTrend ? !isPositive : isPositive

  const formattedValue =
    format === 'percent' ? `${value.toFixed(1)}%` : value.toLocaleString('pt-BR')

  return (
    <div className="rounded-lg bg-secondary p-3 text-center">
      <div className="text-lg font-bold text-foreground">{formattedValue}</div>
      <div className="mb-1 text-xs text-muted-foreground">{label}</div>
      {Math.abs(diff) >= 1 && (
        <div
          className={`flex items-center justify-center text-xs ${
            isGood ? 'text-status-success-foreground' : 'text-status-error-foreground'
          }`}
        >
          {isPositive ? (
            <TrendingUp className="mr-0.5 h-3 w-3" />
          ) : (
            <TrendingDown className="mr-0.5 h-3 w-3" />
          )}
          {isPositive ? '+' : ''}
          {diff.toFixed(0)}%
        </div>
      )}
    </div>
  )
}

const defaultMetrics: ChipPoolAggregatedMetrics = {
  totalMessagesSent: 0,
  previousMessagesSent: 0,
  avgResponseRate: 0,
  previousResponseRate: 0,
  avgBlockRate: 0,
  previousBlockRate: 0,
  totalErrors: 0,
  previousErrors: 0,
}

export function ChipPoolMetricsComponent({ metrics = defaultMetrics }: ChipPoolMetricsProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-foreground/80">Metricas Agregadas (periodo)</h4>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricItem
          label="Msgs Enviadas"
          value={metrics.totalMessagesSent}
          previousValue={metrics.previousMessagesSent}
          format="number"
        />
        <MetricItem
          label="Taxa Resposta"
          value={metrics.avgResponseRate}
          previousValue={metrics.previousResponseRate}
          format="percent"
        />
        <MetricItem
          label="Taxa Block"
          value={metrics.avgBlockRate}
          previousValue={metrics.previousBlockRate}
          format="percent"
          invertTrend
        />
        <MetricItem
          label="Erros"
          value={metrics.totalErrors}
          previousValue={metrics.previousErrors}
          format="number"
          invertTrend
        />
      </div>
    </div>
  )
}
