/**
 * Sparkline Chart Component - Sprint 33 E12
 *
 * Compact line chart showing metric trends over time.
 */

'use client'

import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { type SparklineMetric } from '@/types/dashboard'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SparklineChartProps {
  metric: SparklineMetric
}

// CSS variable-based colors for chart lines (resolved at runtime)
const CHART_COLORS = {
  neutral: 'hsl(var(--muted-foreground))',
  success: 'hsl(var(--status-success-solid))',
  error: 'hsl(var(--status-error-solid))',
} as const

export function SparklineChart({ metric }: SparklineChartProps) {
  const { label, data, currentValue, unit, trend, trendIsGood } = metric

  // Determinar cor da linha baseado na tendencia
  const lineColor =
    trend === 'stable' ? CHART_COLORS.neutral : trendIsGood ? CHART_COLORS.success : CHART_COLORS.error

  // Icone de tendencia
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus

  // Formatar valor
  const formattedValue =
    unit === '%'
      ? `${currentValue.toFixed(1)}%`
      : unit === 's'
        ? `${currentValue.toFixed(0)}s`
        : unit === '$'
          ? `$${currentValue.toFixed(2)}`
          : currentValue.toFixed(0)

  return (
    <div className="flex items-center gap-4 py-2">
      <div className="w-32 text-sm text-muted-foreground">{label}</div>

      <div className="h-8 min-w-[100px] flex-1">
        <ResponsiveContainer width="100%" height={32} minWidth={100}>
          <LineChart data={data}>
            <Line type="monotone" dataKey="value" stroke={lineColor} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex w-20 items-center justify-end gap-2">
        <span className="font-medium">{formattedValue}</span>
        <TrendIcon
          className={cn(
            'h-4 w-4',
            trend === 'stable'
              ? 'text-muted-foreground'
              : trendIsGood
                ? 'text-status-success-foreground'
                : 'text-status-error-foreground'
          )}
        />
      </div>
    </div>
  )
}
