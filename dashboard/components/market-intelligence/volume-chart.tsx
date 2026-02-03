/**
 * VolumeChart - Sprint 46
 *
 * Grafico de area/linha mostrando evolucao de volume ao longo do tempo.
 */

'use client'

import { useState, useMemo } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { VolumeDataPoint } from '@/types/market-intelligence'

// =============================================================================
// TYPES
// =============================================================================

export interface VolumeChartProps {
  data: VolumeDataPoint[] | null
  isLoading?: boolean
  className?: string
  title?: string
}

interface SeriesConfig {
  key: keyof Omit<VolumeDataPoint, 'data'>
  label: string
  color: string
  defaultVisible: boolean
}

// =============================================================================
// CONSTANTS
// =============================================================================

const SERIES_CONFIG: SeriesConfig[] = [
  {
    key: 'mensagens',
    label: 'Mensagens',
    color: '#3b82f6',
    defaultVisible: true,
  },
  { key: 'ofertas', label: 'Ofertas', color: '#f59e0b', defaultVisible: true },
  {
    key: 'vagasExtraidas',
    label: 'Vagas Extraidas',
    color: '#8b5cf6',
    defaultVisible: false,
  },
  {
    key: 'vagasImportadas',
    label: 'Vagas Importadas',
    color: '#10b981',
    defaultVisible: true,
  },
]

// =============================================================================
// HELPERS
// =============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function formatNumber(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}k`
  }
  return String(value)
}

// =============================================================================
// SUBCOMPONENTS
// =============================================================================

function VolumeChartSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader>
        <Skeleton className="h-6 w-40" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[280px] w-full" />
      </CardContent>
    </Card>
  )
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    color: string
    dataKey: string
  }>
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null
  }

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="mb-2 font-medium">{label ? formatDate(label) : ''}</p>
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={entry.dataKey} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="text-sm text-muted-foreground">{entry.name}</span>
            </div>
            <span className="font-medium">{entry.value.toLocaleString('pt-BR')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

interface LegendItemProps {
  label: string
  color: string
  visible: boolean
  onClick: () => void
}

function LegendItem({ label, color, visible, onClick }: LegendItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 rounded-md px-2 py-1 text-sm transition-colors',
        visible ? 'opacity-100' : 'opacity-50'
      )}
      aria-pressed={visible}
      aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${label}`}
    >
      <div
        className={cn('h-3 w-3 rounded-full', !visible && 'ring-1 ring-muted-foreground')}
        style={{ backgroundColor: visible ? color : 'transparent' }}
      />
      <span>{label}</span>
    </button>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function VolumeChart({
  data,
  isLoading = false,
  className,
  title = 'Volume ao Longo do Tempo',
}: VolumeChartProps) {
  // Estado de visibilidade das series
  const [visibleSeries, setVisibleSeries] = useState<Set<string>>(() => {
    const initial = new Set<string>()
    SERIES_CONFIG.forEach((s) => {
      if (s.defaultVisible) {
        initial.add(s.key)
      }
    })
    return initial
  })

  // Toggle de serie
  const toggleSeries = (key: string) => {
    setVisibleSeries((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        // Nao permitir ocultar todas
        if (next.size > 1) {
          next.delete(key)
        }
      } else {
        next.add(key)
      }
      return next
    })
  }

  // Formatar dados para o grafico
  const chartData = useMemo(() => {
    if (!data) return []
    return data.map((d) => ({
      ...d,
      dataFormatada: formatDate(d.data),
    }))
  }, [data])

  // Loading state
  if (isLoading) {
    return <VolumeChartSkeleton />
  }

  // Empty state
  if (!data || data.length === 0) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[280px] items-center justify-center text-muted-foreground">
            Nenhum dado disponivel para o periodo selecionado
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn('flex h-full flex-col', className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle>{title}</CardTitle>
        <div className="flex flex-wrap gap-1">
          {SERIES_CONFIG.map((series) => (
            <LegendItem
              key={series.key}
              label={series.label}
              color={series.color}
              visible={visibleSeries.has(series.key)}
              onClick={() => toggleSeries(series.key)}
            />
          ))}
        </div>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="h-full min-h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                {SERIES_CONFIG.map((series) => (
                  <linearGradient
                    key={`gradient-${series.key}`}
                    id={`gradient-${series.key}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor={series.color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={series.color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>

              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />

              <XAxis
                dataKey="data"
                tickFormatter={formatDate}
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />

              <YAxis
                tickFormatter={formatNumber}
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={40}
              />

              <Tooltip content={<CustomTooltip />} />

              {SERIES_CONFIG.map((series) =>
                visibleSeries.has(series.key) ? (
                  <Area
                    key={series.key}
                    type="monotone"
                    dataKey={series.key}
                    name={series.label}
                    stroke={series.color}
                    fill={`url(#gradient-${series.key})`}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: series.color }}
                  />
                ) : null
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

export default VolumeChart
