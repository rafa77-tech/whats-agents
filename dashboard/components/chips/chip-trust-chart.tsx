/**
 * Chip Trust Chart - Sprint 36
 *
 * Gráfico de histórico de trust score do chip.
 */

'use client'

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { ChipTrustHistory, TrustEvent } from '@/types/chips'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { TrendingDown, TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react'

interface ChipTrustChartProps {
  history: ChipTrustHistory
}

const trustLevelThresholds = [
  { value: 80, label: 'Verde', color: '#22c55e' },
  { value: 60, label: 'Amarelo', color: '#eab308' },
  { value: 40, label: 'Laranja', color: '#f97316' },
  { value: 20, label: 'Vermelho', color: '#ef4444' },
]

const eventTypeConfig: Record<string, { icon: typeof TrendingUp; color: string; bgColor: string }> =
  {
    increase: {
      icon: TrendingUp,
      color: 'text-status-success-solid',
      bgColor: 'bg-status-success/10',
    },
    decrease: {
      icon: TrendingDown,
      color: 'text-status-error-solid',
      bgColor: 'bg-status-error/10',
    },
    phase_change: {
      icon: RefreshCw,
      color: 'text-status-info-solid',
      bgColor: 'bg-status-info/10',
    },
    alert: {
      icon: AlertTriangle,
      color: 'text-status-warning-solid',
      bgColor: 'bg-status-warning/10',
    },
  }

const defaultEventConfig = {
  icon: AlertTriangle,
  color: 'text-muted-foreground',
  bgColor: 'bg-muted/50',
}

export function ChipTrustChart({ history }: ChipTrustChartProps) {
  const chartData = useMemo(() => {
    return history.history.map((point) => ({
      timestamp: new Date(point.timestamp).toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
      }),
      score: point.score,
      level: point.level,
    }))
  }, [history.history])

  const recentEvents = history.events.slice(0, 5)

  const getLineColor = (score: number) => {
    if (score >= 80) return '#22c55e'
    if (score >= 60) return '#eab308'
    if (score >= 40) return '#f97316'
    if (score >= 20) return '#ef4444'
    return '#991b1b'
  }

  const currentScore = chartData[chartData.length - 1]?.score ?? 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>Histórico de Trust Score</span>
          <Badge
            className={cn(
              currentScore >= 80 && 'bg-trust-verde text-trust-verde-foreground',
              currentScore >= 60 &&
                currentScore < 80 &&
                'bg-trust-amarelo text-trust-amarelo-foreground',
              currentScore >= 40 &&
                currentScore < 60 &&
                'bg-trust-laranja text-trust-laranja-foreground',
              currentScore >= 20 &&
                currentScore < 40 &&
                'bg-trust-vermelho text-trust-vermelho-foreground',
              currentScore < 20 && 'bg-trust-critico text-trust-critico-foreground'
            )}
          >
            Atual: {currentScore}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#e5e7eb' }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#e5e7eb' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
                formatter={(value) => [`${value ?? 0}`, 'Trust Score']}
              />
              {trustLevelThresholds.map((threshold) => (
                <ReferenceLine
                  key={threshold.value}
                  y={threshold.value}
                  stroke={threshold.color}
                  strokeDasharray="3 3"
                  strokeOpacity={0.5}
                />
              ))}
              <Line
                type="monotone"
                dataKey="score"
                stroke={getLineColor(currentScore)}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: getLineColor(currentScore) }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Recent events */}
        {recentEvents.length > 0 && (
          <div className="mt-4 border-t border-border pt-4">
            <h4 className="mb-3 text-sm font-medium text-foreground">Eventos Recentes</h4>
            <div className="space-y-2">
              {recentEvents.map((event) => (
                <TrustEventItem key={event.id} event={event} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function TrustEventItem({ event }: { event: TrustEvent }) {
  const config = eventTypeConfig[event.type] || defaultEventConfig
  const Icon = config.icon
  const scoreDiff = event.scoreAfter - event.scoreBefore
  const isPositive = scoreDiff > 0

  return (
    <div className={cn('flex items-start gap-3 rounded-md p-2', config.bgColor)}>
      <div className={cn('rounded p-1', 'bg-background')}>
        <Icon className={cn('h-4 w-4', config.color)} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-foreground">{event.description}</p>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{new Date(event.timestamp).toLocaleString('pt-BR')}</span>
          <span>•</span>
          <span
            className={cn(
              isPositive ? 'text-status-success-foreground' : 'text-status-error-foreground'
            )}
          >
            {isPositive ? '+' : ''}
            {scoreDiff} ({event.scoreBefore} → {event.scoreAfter})
          </span>
        </div>
      </div>
    </div>
  )
}
