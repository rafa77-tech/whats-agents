/**
 * KPICard - Sprint 46
 *
 * Card para exibicao de KPIs com variacao e sparkline.
 */

'use client'

import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { KPICardProps } from '@/types/market-intelligence'

// =============================================================================
// SPARKLINE
// =============================================================================

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
}

function Sparkline({ data, width = 80, height = 24, className }: SparklineProps) {
  if (!data || data.length < 2) {
    return null
  }

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  // Normalizar valores para altura do SVG
  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * width
      const y = height - ((value - min) / range) * height
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg
      width={width}
      height={height}
      className={cn('overflow-visible', className)}
      role="img"
      aria-label="Grafico de tendencia"
    >
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-muted-foreground/50"
      />
      {/* Ponto final destacado */}
      {(() => {
        const lastValue = data[data.length - 1]
        if (data.length > 0 && lastValue !== undefined) {
          return (
            <circle
              cx={width}
              cy={height - ((lastValue - min) / range) * height}
              r="2"
              fill="currentColor"
              className="text-foreground"
            />
          )
        }
        return null
      })()}
    </svg>
  )
}

// =============================================================================
// VARIACAO INDICATOR
// =============================================================================

interface VariacaoIndicatorProps {
  variacao: number | null
  tipo: 'up' | 'down' | 'stable' | null
}

function VariacaoIndicator({ variacao, tipo }: VariacaoIndicatorProps) {
  if (variacao === null || tipo === null) {
    return null
  }

  const config = {
    up: {
      icon: TrendingUp,
      color: 'text-status-success-foreground',
      bgColor: 'bg-status-success/10',
      label: 'Aumento',
    },
    down: {
      icon: TrendingDown,
      color: 'text-status-error-foreground',
      bgColor: 'bg-status-error/10',
      label: 'Reducao',
    },
    stable: {
      icon: Minus,
      color: 'text-muted-foreground',
      bgColor: 'bg-muted',
      label: 'Estavel',
    },
  }

  const { icon: Icon, color, bgColor, label } = config[tipo]
  const formattedVariacao = variacao > 0 ? `+${variacao}` : String(variacao)

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        bgColor,
        color
      )}
      role="status"
      aria-label={`${label} de ${Math.abs(variacao)}%`}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      <span>{formattedVariacao}%</span>
    </div>
  )
}

// =============================================================================
// STATUS INDICATOR
// =============================================================================

interface StatusIndicatorProps {
  status: 'success' | 'warning' | 'danger' | 'neutral'
}

function StatusIndicator({ status }: StatusIndicatorProps) {
  const config = {
    success: 'bg-status-success-solid',
    warning: 'bg-status-warning-solid',
    danger: 'bg-status-error-solid',
    neutral: 'bg-muted-foreground',
  }

  return (
    <span
      className={cn('h-2 w-2 rounded-full', config[status])}
      role="status"
      aria-label={`Status: ${status}`}
    />
  )
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

export function KPICardSkeleton() {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-5 rounded" />
              <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-6 w-20" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

function KPICardComponent({
  titulo,
  valor,
  valorFormatado,
  subtitulo,
  icone,
  variacao,
  variacaoTipo,
  tendencia,
  status = 'neutral',
  loading = false,
  className,
}: KPICardProps) {
  // Loading state
  if (loading) {
    return <KPICardSkeleton />
  }

  const displayValue = valorFormatado ?? String(valor)

  return (
    <Card className={cn('transition-shadow hover:shadow-md', className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Lado esquerdo: icone, titulo, valor */}
          <div className="min-w-0 flex-1">
            {/* Header com icone e titulo */}
            <div className="mb-2 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                {icone}
              </div>
              <span className="text-sm font-medium text-muted-foreground">{titulo}</span>
              <StatusIndicator status={status} />
            </div>

            {/* Valor principal */}
            <div className="mb-1">
              <span className="text-2xl font-bold text-foreground">{displayValue}</span>
            </div>

            {/* Subtitulo */}
            {subtitulo && <span className="text-xs text-muted-foreground">{subtitulo}</span>}
          </div>

          {/* Lado direito: variacao e sparkline */}
          <div className="flex flex-col items-end gap-2">
            <VariacaoIndicator variacao={variacao ?? null} tipo={variacaoTipo ?? null} />
            {tendencia && tendencia.length > 1 && <Sparkline data={tendencia} />}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Exportar com memo para evitar re-renders desnecessarios
export const KPICard = memo(KPICardComponent)
KPICard.displayName = 'KPICard'
