/**
 * PipelineFunnel - Sprint 46
 *
 * Visualizacao do funil de processamento do pipeline.
 */

'use client'

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { ArrowDown, AlertTriangle, XCircle } from 'lucide-react'
import type {
  PipelineFunil,
  PipelineEtapa,
  PipelineConversoes,
  PipelinePerdas,
} from '@/types/market-intelligence'

// =============================================================================
// TYPES
// =============================================================================

export interface PipelineFunnelProps {
  data: PipelineFunil | null
  perdas?: PipelinePerdas | null
  isLoading?: boolean
  className?: string
  title?: string
  showPerdas?: boolean
  /** Modo compacto: exibe apenas o funil sem cards auxiliares */
  compact?: boolean
}

// =============================================================================
// CONSTANTS
// =============================================================================

const STAGE_COLORS: Record<string, string> = {
  mensagens: 'bg-blue-500',
  heuristica: 'bg-blue-400',
  ofertas: 'bg-indigo-500',
  extraidas: 'bg-violet-500',
  validadas: 'bg-purple-500',
  importadas: 'bg-green-500',
}

const STAGE_BG_COLORS: Record<string, string> = {
  mensagens: 'bg-blue-100 dark:bg-blue-950',
  heuristica: 'bg-blue-50 dark:bg-blue-950',
  ofertas: 'bg-indigo-100 dark:bg-indigo-950',
  extraidas: 'bg-violet-100 dark:bg-violet-950',
  validadas: 'bg-purple-100 dark:bg-purple-950',
  importadas: 'bg-green-100 dark:bg-green-950',
}

// =============================================================================
// HELPERS
// =============================================================================

function formatNumber(value: number): string {
  return value.toLocaleString('pt-BR')
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

// =============================================================================
// SUBCOMPONENTS
// =============================================================================

function PipelineFunnelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
      </CardHeader>
      <CardContent className="space-y-4">
        {[100, 80, 60, 40, 30, 20].map((width, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10" style={{ width: `${width}%` }} />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

interface FunnelStageProps {
  etapa: PipelineEtapa
  isLast: boolean
  conversaoProxima?: number | undefined
}

interface FunnelStageCompactProps {
  etapa: PipelineEtapa
}

function FunnelStageCompact({ etapa }: FunnelStageCompactProps) {
  const barColor = STAGE_COLORS[etapa.id] || 'bg-gray-500'
  const bgColor = STAGE_BG_COLORS[etapa.id] || 'bg-gray-100'
  // Limitar percentual a 100% para a largura da barra
  const barWidth = Math.min(Math.max(etapa.percentual, 3), 100)

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-3 rounded p-1">
            <span className="w-28 truncate text-sm font-medium text-foreground">{etapa.nome}</span>
            <div className={cn('h-5 flex-1 overflow-hidden rounded', bgColor)}>
              <div
                className={cn(
                  'flex h-full items-center justify-end rounded pr-2 text-xs font-medium text-white',
                  barColor
                )}
                style={{ width: `${barWidth}%`, minWidth: barWidth > 0 ? '24px' : '0' }}
              >
                {barWidth >= 15 && formatPercent(Math.min(etapa.percentual, 100))}
              </div>
            </div>
            <span className="w-14 text-right text-sm font-semibold tabular-nums">
              {formatNumber(etapa.valor)}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>
            {etapa.nome} - {formatNumber(etapa.valor)} ({formatPercent(etapa.percentual)})
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function FunnelStage({ etapa, isLast, conversaoProxima }: FunnelStageProps) {
  const barColor = STAGE_COLORS[etapa.id] || 'bg-gray-500'
  const bgColor = STAGE_BG_COLORS[etapa.id] || 'bg-gray-100'
  // Limitar percentual a 100% para a largura da barra
  const barWidth = Math.min(Math.max(etapa.percentual, 5), 100)

  return (
    <div className="space-y-1">
      {/* Label */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{etapa.nome}</span>
        <span className="text-muted-foreground">
          {formatNumber(etapa.valor)} ({formatPercent(etapa.percentual)})
        </span>
      </div>

      {/* Bar */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={cn('h-10 rounded-md transition-all', bgColor)}>
              <div
                className={cn(
                  'flex h-full items-center justify-center rounded-md text-sm font-medium text-white transition-all',
                  barColor
                )}
                style={{ width: `${barWidth}%` }}
              >
                {barWidth >= 15 && formatPercent(Math.min(etapa.percentual, 100))}
              </div>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <p className="font-medium">{etapa.nome}</p>
              <p>Total: {formatNumber(etapa.valor)}</p>
              <p>Percentual: {formatPercent(etapa.percentual)}</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Conversion arrow */}
      {!isLast && conversaoProxima !== undefined && (
        <div className="flex items-center justify-center py-1 text-muted-foreground">
          <ArrowDown className="h-4 w-4" />
          <span className="ml-1 text-xs">
            {formatPercent(Math.min(conversaoProxima, 100))} convertido
          </span>
        </div>
      )}
    </div>
  )
}

interface PerdasCardProps {
  perdas: PipelinePerdas
}

function PerdasCard({ perdas }: PerdasCardProps) {
  const items = [
    {
      label: 'Duplicadas',
      value: perdas.duplicadas,
      icon: XCircle,
      color: 'text-orange-500',
    },
    {
      label: 'Descartadas',
      value: perdas.descartadas,
      icon: XCircle,
      color: 'text-red-500',
    },
    {
      label: 'Em Revisao',
      value: perdas.revisao,
      icon: AlertTriangle,
      color: 'text-yellow-500',
    },
    {
      label: 'Sem Dados Minimos',
      value: perdas.semDadosMinimos,
      icon: AlertTriangle,
      color: 'text-orange-500',
    },
  ]

  const total = items.reduce((acc, item) => acc + item.value, 0)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Perdas no Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {items.map((item) => {
            const Icon = item.icon
            return (
              <div key={item.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className={cn('h-4 w-4', item.color)} />
                  <span className="text-sm">{item.label}</span>
                </div>
                <span className="font-medium">{formatNumber(item.value)}</span>
              </div>
            )
          })}
          <div className="flex items-center justify-between border-t pt-2">
            <span className="text-sm font-medium">Total de Perdas</span>
            <span className="font-bold">{formatNumber(total)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface ConversaoResumoProps {
  conversoes: PipelineConversoes
}

function ConversaoResumo({ conversoes }: ConversaoResumoProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Taxas de Conversao</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Msg → Oferta</p>
            <p className="text-lg font-bold">{formatPercent(conversoes.mensagemParaOferta)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Oferta → Extracao</p>
            <p className="text-lg font-bold">{formatPercent(conversoes.ofertaParaExtracao)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Extracao → Import</p>
            <p className="text-lg font-bold">{formatPercent(conversoes.extracaoParaImportacao)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Pipeline Total</p>
            <p className="text-lg font-bold text-green-600">
              {formatPercent(conversoes.totalPipeline)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function PipelineFunnel({
  data,
  perdas,
  isLoading = false,
  className,
  title = 'Funil do Pipeline',
  showPerdas = true,
  compact = false,
}: PipelineFunnelProps) {
  // Calcular conversoes entre etapas adjacentes
  const etapasComConversao = useMemo(() => {
    if (!data?.etapas) return []

    return data.etapas.map((etapa, index) => {
      let conversaoProxima: number | undefined

      if (index < data.etapas.length - 1) {
        const proxima = data.etapas[index + 1]
        if (proxima && etapa.valor > 0) {
          conversaoProxima = (proxima.valor / etapa.valor) * 100
        }
      }

      return { etapa, conversaoProxima }
    })
  }, [data])

  // Loading state
  if (isLoading) {
    return <PipelineFunnelSkeleton />
  }

  // Empty state
  if (!data || !data.etapas || data.etapas.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            Nenhum dado disponivel para o periodo selecionado
          </div>
        </CardContent>
      </Card>
    )
  }

  // Modo compacto: layout condensado sem arrows de conversão
  if (compact) {
    return (
      <Card className={cn('flex h-full flex-col', className)}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col justify-between">
          <div className="space-y-2.5">
            {data.etapas.map((etapa) => (
              <FunnelStageCompact key={etapa.id} etapa={etapa} />
            ))}
          </div>
          {/* Resumo de conversão no rodapé */}
          {data.conversoes && (
            <div className="mt-4 flex items-center justify-between border-t pt-3 text-xs">
              <span className="text-muted-foreground">Taxa total do pipeline</span>
              <span className="font-bold text-green-600">
                {formatPercent(Math.min(data.conversoes.totalPipeline, 100))}
              </span>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Funil Principal */}
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {etapasComConversao.map(({ etapa, conversaoProxima }, index) => (
            <FunnelStage
              key={etapa.id}
              etapa={etapa}
              isLast={index === etapasComConversao.length - 1}
              conversaoProxima={conversaoProxima}
            />
          ))}
        </CardContent>
      </Card>

      {/* Cards Auxiliares */}
      <div className="grid gap-4 md:grid-cols-2">
        {data.conversoes && <ConversaoResumo conversoes={data.conversoes} />}
        {showPerdas && perdas && <PerdasCard perdas={perdas} />}
      </div>
    </div>
  )
}

export default PipelineFunnel
