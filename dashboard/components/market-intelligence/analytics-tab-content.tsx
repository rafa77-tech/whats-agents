/**
 * AnalyticsTabContent - Sprint 46
 *
 * Conteudo da aba Analytics no modulo de Grupos.
 */

'use client'

import { useMarketIntelligence } from '@/hooks/use-market-intelligence'
import { KPICard } from './kpi-card'
import { VolumeChart } from './volume-chart'
import { PipelineFunnel } from './pipeline-funnel'
import { GroupsRanking } from './groups-ranking'
import { PeriodSelector } from './period-selector'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  RefreshCw,
  Clock,
  AlertCircle,
  Users,
  Briefcase,
  TrendingUp,
  DollarSign,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AnalyticsPeriod } from '@/types/market-intelligence'

// =============================================================================
// TYPES
// =============================================================================

export interface AnalyticsTabContentProps {
  className?: string
}

// =============================================================================
// HELPERS
// =============================================================================

function formatLastUpdated(date: Date | null): string {
  if (!date) return ''
  return date.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

// =============================================================================
// SUBCOMPONENTS
// =============================================================================

function LoadingState() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-32" />
      </div>

      {/* KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-[350px] lg:col-span-2" />
        <Skeleton className="h-[350px]" />
      </div>

      {/* Ranking */}
      <Skeleton className="h-[400px]" />
    </div>
  )
}

function ErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center">
      <AlertCircle className="h-12 w-12 text-destructive" />
      <div>
        <h3 className="text-lg font-semibold">Erro ao carregar dados</h3>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
      <Button onClick={onRetry} variant="outline">
        <RefreshCw className="mr-2 h-4 w-4" />
        Tentar novamente
      </Button>
    </div>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function AnalyticsTabContent({ className }: AnalyticsTabContentProps) {
  const {
    overview,
    volume,
    pipeline,
    isLoading,
    isRefreshing,
    error,
    refresh,
    setPeriod,
    setCustomPeriod,
    lastUpdated,
    period,
  } = useMarketIntelligence()

  // Handler para mudanca de periodo
  const handlePeriodChange = (newPeriod: AnalyticsPeriod) => {
    setPeriod(newPeriod)
  }

  // Handler para periodo customizado
  const handleCustomPeriod = (startDate: string, endDate: string) => {
    setCustomPeriod(startDate, endDate)
  }

  // Loading inicial
  if (isLoading && !overview) {
    return <LoadingState />
  }

  // Erro
  if (error && !overview) {
    return <ErrorState error={error} onRetry={refresh} />
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PeriodSelector
          value={period}
          onChange={handlePeriodChange}
          onCustomChange={handleCustomPeriod}
        />

        <div className="flex items-center gap-4">
          {lastUpdated && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>Atualizado as {formatLastUpdated(lastUpdated)}</span>
            </div>
          )}

          <Button variant="outline" size="sm" onClick={refresh} disabled={isRefreshing}>
            <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} />
            {isRefreshing ? 'Atualizando...' : 'Atualizar'}
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          titulo="Grupos Ativos"
          valor={overview?.kpis.gruposAtivos.valor ?? 0}
          valorFormatado={overview?.kpis.gruposAtivos.valorFormatado ?? '-'}
          icone={<Users className="h-4 w-4" />}
          variacao={overview?.kpis.gruposAtivos.variacao ?? null}
          variacaoTipo={overview?.kpis.gruposAtivos.variacaoTipo ?? null}
          tendencia={overview?.kpis.gruposAtivos.tendencia ?? []}
          loading={isRefreshing}
        />
        <KPICard
          titulo="Vagas por Dia"
          valor={overview?.kpis.vagasPorDia.valor ?? 0}
          valorFormatado={overview?.kpis.vagasPorDia.valorFormatado ?? '-'}
          icone={<Briefcase className="h-4 w-4" />}
          variacao={overview?.kpis.vagasPorDia.variacao ?? null}
          variacaoTipo={overview?.kpis.vagasPorDia.variacaoTipo ?? null}
          tendencia={overview?.kpis.vagasPorDia.tendencia ?? []}
          loading={isRefreshing}
        />
        <KPICard
          titulo="Taxa de Conversao"
          valor={overview?.kpis.taxaConversao.valor ?? 0}
          valorFormatado={overview?.kpis.taxaConversao.valorFormatado ?? '-'}
          icone={<TrendingUp className="h-4 w-4" />}
          variacao={overview?.kpis.taxaConversao.variacao ?? null}
          variacaoTipo={overview?.kpis.taxaConversao.variacaoTipo ?? null}
          tendencia={overview?.kpis.taxaConversao.tendencia ?? []}
          loading={isRefreshing}
        />
        <KPICard
          titulo="Valor Medio"
          valor={overview?.kpis.valorMedio.valor ?? 0}
          valorFormatado={overview?.kpis.valorMedio.valorFormatado ?? '-'}
          icone={<DollarSign className="h-4 w-4" />}
          variacao={overview?.kpis.valorMedio.variacao ?? null}
          variacaoTipo={overview?.kpis.valorMedio.variacaoTipo ?? null}
          tendencia={overview?.kpis.valorMedio.tendencia ?? []}
          loading={isRefreshing}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <VolumeChart data={volume?.dados ?? null} isLoading={isRefreshing} />
        </div>
        <div>
          <PipelineFunnel
            data={pipeline?.funil ?? null}
            perdas={pipeline?.perdas ?? null}
            isLoading={isRefreshing}
            showPerdas={false}
          />
        </div>
      </div>

      {/* Pipeline detalhado + Ranking */}
      <div className="grid gap-4 lg:grid-cols-2">
        <PipelineFunnel
          data={pipeline?.funil ?? null}
          perdas={pipeline?.perdas ?? null}
          isLoading={isRefreshing}
          title="Detalhes do Pipeline"
        />
        <GroupsRanking
          data={null} // TODO: Integrar com API de ranking
          isLoading={isRefreshing}
          limit={5}
          title="Top 5 Grupos"
        />
      </div>
    </div>
  )
}

export default AnalyticsTabContent
