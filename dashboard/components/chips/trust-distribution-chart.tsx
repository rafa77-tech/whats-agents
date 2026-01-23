/**
 * Trust Distribution Chart - Sprint 36
 *
 * Gráfico de distribuição de trust score do pool.
 */

'use client'

import { useMemo } from 'react'
import { TrustLevelExtended } from '@/types/chips'
import { cn } from '@/lib/utils'

interface TrustDistributionChartProps {
  distribution: Record<TrustLevelExtended, number>
  total: number
}

const trustLevelConfig: Record<
  TrustLevelExtended,
  { label: string; color: string; bgColor: string }
> = {
  verde: { label: 'Verde (80-100)', color: 'bg-green-500', bgColor: 'bg-green-100' },
  amarelo: { label: 'Amarelo (60-79)', color: 'bg-yellow-500', bgColor: 'bg-yellow-100' },
  laranja: { label: 'Laranja (40-59)', color: 'bg-orange-500', bgColor: 'bg-orange-100' },
  vermelho: { label: 'Vermelho (20-39)', color: 'bg-red-500', bgColor: 'bg-red-100' },
  critico: { label: 'Critico (0-19)', color: 'bg-gray-500', bgColor: 'bg-gray-100' },
}

const displayOrder: TrustLevelExtended[] = ['verde', 'amarelo', 'laranja', 'vermelho', 'critico']

export function TrustDistributionChart({ distribution, total }: TrustDistributionChartProps) {
  const data = useMemo(() => {
    return displayOrder.map((level) => ({
      level,
      count: distribution[level] || 0,
      percentage: total > 0 ? ((distribution[level] || 0) / total) * 100 : 0,
      config: trustLevelConfig[level],
    }))
  }, [distribution, total])

  const healthyPercentage = useMemo(() => {
    const healthy = (distribution.verde || 0) + (distribution.amarelo || 0)
    return total > 0 ? (healthy / total) * 100 : 0
  }, [distribution, total])

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Distribuicao de Trust Score</h3>
        <div className="text-sm">
          <span
            className={cn(
              'font-medium',
              healthyPercentage >= 70
                ? 'text-green-600'
                : healthyPercentage >= 50
                  ? 'text-yellow-600'
                  : 'text-red-600'
            )}
          >
            {healthyPercentage.toFixed(1)}% saudaveis
          </span>
        </div>
      </div>

      {/* Stacked bar */}
      <div className="mb-6">
        <div className="flex h-8 overflow-hidden rounded-full bg-gray-100">
          {data.map(
            ({ level, percentage, config }) =>
              percentage > 0 && (
                <div
                  key={level}
                  className={cn('h-full transition-all', config.color)}
                  style={{ width: `${percentage}%` }}
                  title={`${config.label}: ${percentage.toFixed(1)}%`}
                />
              )
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {data.map(({ level, count, config }) => (
          <div key={level} className="flex items-center gap-2">
            <div className={cn('h-3 w-3 rounded-full', config.color)} />
            <div>
              <p className="text-sm font-medium text-gray-900">{count}</p>
              <p className="text-xs text-gray-500">{config.label.split(' ')[0]}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
