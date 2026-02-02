/**
 * Funnel Stage Component - Sprint 33 E10
 *
 * Individual stage bar for the conversion funnel visualization.
 */

'use client'

import { type FunnelStageVisual } from '@/types/dashboard'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

interface FunnelStageProps {
  stage: FunnelStageVisual
  maxCount: number // para calcular largura relativa
  onClick: () => void
  isFirst: boolean
}

const stageColors: Record<string, { bg: string; border: string; text: string }> = {
  enviadas: {
    bg: 'bg-status-info',
    border: 'border-status-info-border',
    text: 'text-status-info-foreground',
  },
  entregues: {
    bg: 'bg-status-info',
    border: 'border-status-info-border',
    text: 'text-status-info-foreground',
  },
  respostas: {
    bg: 'bg-status-success',
    border: 'border-status-success-border',
    text: 'text-status-success-foreground',
  },
  interesse: {
    bg: 'bg-status-warning',
    border: 'border-status-warning-border',
    text: 'text-status-warning-foreground',
  },
  fechadas: {
    bg: 'bg-status-success',
    border: 'border-status-success-border',
    text: 'text-status-success-foreground',
  },
}

export function FunnelStageComponent({ stage, maxCount, onClick, isFirst }: FunnelStageProps) {
  const { id, label, count, previousCount, percentage } = stage

  // Calcular largura proporcional (minimo 30% para legibilidade)
  const widthPercent = Math.max(30, (count / maxCount) * 100)

  // Calcular variacao
  const diff = previousCount > 0 ? ((count - previousCount) / previousCount) * 100 : 0
  const isPositive = diff > 0

  const colors = stageColors[id] ?? {
    bg: 'bg-status-info',
    border: 'border-status-info-border',
    text: 'text-status-info-foreground',
  }

  const paddingValue = isFirst ? 0 : (100 - widthPercent) / 2

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="flex cursor-pointer justify-center transition-transform hover:scale-[1.02]"
            onClick={onClick}
            style={{
              paddingLeft: `${paddingValue}%`,
              paddingRight: `${paddingValue}%`,
            }}
          >
            <div
              className={`w-full rounded-lg border-2 px-4 py-3 ${colors.bg} ${colors.border} flex items-center justify-between`}
            >
              <div className="flex items-center gap-2">
                <span className={`font-medium ${colors.text}`}>{label}:</span>
                <span className="font-bold text-foreground">{count.toLocaleString('pt-BR')}</span>
                <span className="text-sm text-muted-foreground">({percentage.toFixed(1)}%)</span>
              </div>

              {Math.abs(diff) >= 1 && (
                <div
                  className={`flex items-center text-sm ${
                    isPositive ? 'text-status-success-foreground' : 'text-status-error-foreground'
                  }`}
                >
                  {isPositive ? (
                    <TrendingUp className="mr-1 h-4 w-4" />
                  ) : (
                    <TrendingDown className="mr-1 h-4 w-4" />
                  )}
                  {isPositive ? '+' : ''}
                  {diff.toFixed(0)}%
                </div>
              )}
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>Clique para ver detalhes de {label.toLowerCase()}</p>
          <p className="text-xs text-muted-foreground/70">
            Periodo anterior: {previousCount.toLocaleString('pt-BR')}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
