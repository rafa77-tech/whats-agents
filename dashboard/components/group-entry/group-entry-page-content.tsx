'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  RefreshCw,
  Settings,
  Upload,
  Loader2,
  CheckCircle2,
  Clock,
  Play,
  ChevronDown,
  AlertCircle,
  Users,
  Briefcase,
  TrendingUp,
  DollarSign,
  FolderOpen,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from '@/hooks/use-toast'
import { CapacityBar } from './capacity-bar'
import { LinksTable } from './links-table'
import { ProcessingQueue } from './processing-queue'
import { ImportLinksModal } from './import-links-modal'
import { GroupEntryConfigModal } from './group-entry-config-modal'
import { useGroupEntryDashboard, useBatchActions } from '@/lib/group-entry'
import { useMarketIntelligence } from '@/hooks/use-market-intelligence'
import { KPICard } from '@/components/market-intelligence/kpi-card'
import { VolumeChart } from '@/components/market-intelligence/volume-chart'
import { PipelineFunnel } from '@/components/market-intelligence/pipeline-funnel'
import { GroupsRanking } from '@/components/market-intelligence/groups-ranking'
import { PeriodSelector } from '@/components/market-intelligence/period-selector'
import { VagasHoje } from '@/components/market-intelligence/vagas-hoje'
import { Skeleton } from '@/components/ui/skeleton'
import type { AnalyticsPeriod } from '@/types/market-intelligence'

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
// LOADING STATE
// =============================================================================

function AnalyticsLoadingState() {
  return (
    <div className="space-y-6">
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

// =============================================================================
// ERROR STATE
// =============================================================================

function AnalyticsErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center">
      <AlertCircle className="h-12 w-12 text-destructive" />
      <div>
        <h3 className="text-lg font-semibold">Erro ao carregar analytics</h3>
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

export function GroupEntryPageContent() {
  const [operationsOpen, setOperationsOpen] = useState(false)
  const [operationsTab, setOperationsTab] = useState('links')
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [isConfigOpen, setIsConfigOpen] = useState(false)

  // Hook de analytics (sempre carrega)
  const {
    overview,
    volume,
    pipeline,
    groupsRanking,
    isLoading: analyticsLoading,
    isRefreshing: analyticsRefreshing,
    error: analyticsError,
    refresh: refreshAnalytics,
    setPeriod,
    setCustomPeriod,
    lastUpdated,
    period,
  } = useMarketIntelligence()

  // Hook de operacoes (sempre carrega, mas menos prioritario visualmente)
  const {
    data,
    loading: operationsLoading,
    error: operationsError,
    refresh: refreshOperations,
  } = useGroupEntryDashboard()
  const {
    processingAction,
    error: batchError,
    validatePending,
    scheduleValidated,
    processQueue,
  } = useBatchActions(refreshOperations)

  // Combinar refresh
  const handleRefresh = () => {
    refreshAnalytics()
    refreshOperations()
  }

  // Show error toasts
  useEffect(() => {
    if (operationsError) {
      toast({
        title: 'Erro ao carregar operacoes',
        description: operationsError,
        variant: 'destructive',
      })
    }
  }, [operationsError])

  useEffect(() => {
    if (batchError) {
      toast({
        title: 'Erro na acao',
        description: batchError,
        variant: 'destructive',
      })
    }
  }, [batchError])

  const handleValidatePending = async () => {
    const success = await validatePending()
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Links validados com sucesso',
      })
    }
  }

  const handleScheduleValidated = async () => {
    const success = await scheduleValidated()
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Links agendados com sucesso',
      })
    }
  }

  const handleProcessQueue = async () => {
    const success = await processQueue()
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Fila processada com sucesso',
      })
    }
  }

  // Handlers para periodo
  const handlePeriodChange = (newPeriod: AnalyticsPeriod) => {
    setPeriod(newPeriod)
  }

  const handleCustomPeriod = (startDate: string, endDate: string) => {
    setCustomPeriod(startDate, endDate)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Grupos WhatsApp</h1>
          <p className="text-muted-foreground">Inteligencia de mercado e gestao de grupos</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodSelector
            value={period}
            onChange={handlePeriodChange}
            onCustomChange={handleCustomPeriod}
          />
          {lastUpdated && (
            <div className="hidden items-center gap-1 text-sm text-muted-foreground lg:flex">
              <Clock className="h-4 w-4" />
              <span>{formatLastUpdated(lastUpdated)}</span>
            </div>
          )}
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={analyticsRefreshing || operationsLoading}
          >
            <RefreshCw
              className={cn(
                'h-4 w-4',
                (analyticsRefreshing || operationsLoading) && 'animate-spin'
              )}
            />
          </Button>
        </div>
      </div>

      {/* Analytics Section - Sempre Visivel */}
      {analyticsLoading && !overview ? (
        <AnalyticsLoadingState />
      ) : analyticsError && !overview ? (
        <AnalyticsErrorState error={analyticsError} onRetry={refreshAnalytics} />
      ) : (
        <>
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
              loading={analyticsRefreshing}
            />
            <KPICard
              titulo="Vagas por Dia"
              valor={overview?.kpis.vagasPorDia.valor ?? 0}
              valorFormatado={overview?.kpis.vagasPorDia.valorFormatado ?? '-'}
              icone={<Briefcase className="h-4 w-4" />}
              variacao={overview?.kpis.vagasPorDia.variacao ?? null}
              variacaoTipo={overview?.kpis.vagasPorDia.variacaoTipo ?? null}
              tendencia={overview?.kpis.vagasPorDia.tendencia ?? []}
              loading={analyticsRefreshing}
            />
            <KPICard
              titulo="Taxa de Conversao"
              valor={overview?.kpis.taxaConversao.valor ?? 0}
              valorFormatado={overview?.kpis.taxaConversao.valorFormatado ?? '-'}
              icone={<TrendingUp className="h-4 w-4" />}
              variacao={overview?.kpis.taxaConversao.variacao ?? null}
              variacaoTipo={overview?.kpis.taxaConversao.variacaoTipo ?? null}
              tendencia={overview?.kpis.taxaConversao.tendencia ?? []}
              loading={analyticsRefreshing}
            />
            <KPICard
              titulo="Valor Medio"
              valor={overview?.kpis.valorMedio.valor ?? 0}
              valorFormatado={overview?.kpis.valorMedio.valorFormatado ?? '-'}
              icone={<DollarSign className="h-4 w-4" />}
              variacao={overview?.kpis.valorMedio.variacao ?? null}
              variacaoTipo={overview?.kpis.valorMedio.variacaoTipo ?? null}
              tendencia={overview?.kpis.valorMedio.tendencia ?? []}
              loading={analyticsRefreshing}
            />
          </div>

          {/* Charts Row - Layout equilibrado com altura igual */}
          <div className="grid auto-rows-fr gap-4 lg:grid-cols-2">
            <VolumeChart data={volume?.dados ?? null} isLoading={analyticsRefreshing} />
            <PipelineFunnel
              data={pipeline?.funil ?? null}
              perdas={pipeline?.perdas ?? null}
              isLoading={analyticsRefreshing}
              compact
              title="Pipeline de Vagas"
            />
          </div>

          {/* Groups Ranking */}
          <GroupsRanking
            data={groupsRanking}
            isLoading={analyticsRefreshing}
            limit={5}
            title="Top 5 Grupos por Performance"
          />
        </>
      )}

      {/* Operacoes - Secao Colapsavel */}
      <Collapsible open={operationsOpen} onOpenChange={setOperationsOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="outline" className="flex w-full items-center justify-between py-6">
            <div className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5" />
              <span className="font-medium">Operacoes de Entrada em Grupos</span>
              {data && (
                <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  {data.links.pending || 0} pendentes | {data.queue.queued || 0} na fila
                </span>
              )}
            </div>
            <ChevronDown
              className={cn('h-5 w-5 transition-transform', operationsOpen && 'rotate-180')}
            />
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <Card className="mt-4">
            <CardContent className="pt-6">
              {/* Capacity Bar */}
              <div className="mb-6">
                <CapacityBar used={data?.capacity.used || 0} total={data?.capacity.total || 100} />
              </div>

              {/* Quick Actions */}
              <div className="mb-6">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">Acoes Rapidas</span>
                  <div className="flex gap-2">
                    <Button onClick={() => setIsImportOpen(true)} variant="outline" size="sm">
                      <Upload className="mr-2 h-4 w-4" />
                      Importar
                    </Button>
                    <Button onClick={() => setIsConfigOpen(true)} variant="outline" size="sm">
                      <Settings className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={handleValidatePending}
                    variant="outline"
                    size="sm"
                    disabled={processingAction !== null || (data?.links.pending || 0) === 0}
                  >
                    {processingAction === 'validate' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                    )}
                    Validar Pendentes ({data?.links.pending || 0})
                  </Button>
                  <Button
                    onClick={handleScheduleValidated}
                    variant="outline"
                    size="sm"
                    disabled={processingAction !== null || (data?.links.validated || 0) === 0}
                  >
                    {processingAction === 'schedule' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Clock className="mr-2 h-4 w-4" />
                    )}
                    Agendar Validados ({data?.links.validated || 0})
                  </Button>
                  <Button
                    onClick={handleProcessQueue}
                    variant="outline"
                    size="sm"
                    disabled={processingAction !== null || (data?.queue.queued || 0) === 0}
                  >
                    {processingAction === 'process' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Processar Fila ({data?.queue.queued || 0})
                  </Button>
                </div>
              </div>

              {/* Tabs Links/Fila */}
              <Tabs value={operationsTab} onValueChange={setOperationsTab}>
                <TabsList>
                  <TabsTrigger value="links">Links</TabsTrigger>
                  <TabsTrigger value="queue">Fila</TabsTrigger>
                </TabsList>

                <TabsContent value="links">
                  <LinksTable onUpdate={refreshOperations} />
                </TabsContent>

                <TabsContent value="queue">
                  <ProcessingQueue onUpdate={refreshOperations} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>

      {/* Vagas por Grupo + Vagas Importadas Hoje */}
      <VagasHoje />

      {/* Modals */}
      {isImportOpen && (
        <ImportLinksModal
          onClose={() => setIsImportOpen(false)}
          onImport={() => {
            setIsImportOpen(false)
            refreshOperations()
          }}
        />
      )}

      {isConfigOpen && (
        <GroupEntryConfigModal
          onClose={() => setIsConfigOpen(false)}
          onSave={() => {
            setIsConfigOpen(false)
            refreshOperations()
          }}
        />
      )}
    </div>
  )
}
