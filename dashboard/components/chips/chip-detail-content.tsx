/**
 * Chip Detail Content - Sprint 36
 *
 * Conteúdo principal da página de detalhes do chip.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { useRouter } from 'next/navigation'
import {
  ChevronLeft,
  RefreshCw,
  Phone,
  Activity,
  MessageSquare,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { ChipDetailSkeleton } from './chip-detail-skeleton'
import { ChipTrustChart } from './chip-trust-chart'
import { ChipMetricsCards } from './chip-metrics-cards'
import { ChipInteractionsTimeline } from './chip-interactions-timeline'
import { ChipActionsPanel } from './chip-actions-panel'
import {
  ChipFullDetail,
  ChipMetrics,
  ChipTrustHistory,
  ChipInteractionsResponse,
  TrustLevelExtended,
  WarmupPhase,
} from '@/types/chips'
import { ChipStatus } from '@/types/dashboard'

interface ChipDetailContentProps {
  chipId: string
}

const statusConfig: Record<ChipStatus, { label: string; color: string }> = {
  provisioned: { label: 'Provisionado', color: 'bg-gray-100 text-gray-800' },
  pending: { label: 'Pendente', color: 'bg-yellow-100 text-yellow-800' },
  warming: { label: 'Aquecendo', color: 'bg-blue-100 text-blue-800' },
  ready: { label: 'Pronto', color: 'bg-green-100 text-green-800' },
  active: { label: 'Ativo', color: 'bg-emerald-100 text-emerald-800' },
  degraded: { label: 'Degradado', color: 'bg-orange-100 text-orange-800' },
  paused: { label: 'Pausado', color: 'bg-gray-100 text-gray-800' },
  banned: { label: 'Banido', color: 'bg-red-100 text-red-800' },
  cancelled: { label: 'Cancelado', color: 'bg-red-100 text-red-800' },
  offline: { label: 'Offline', color: 'bg-red-100 text-red-800' },
}

const trustLevelConfig: Record<TrustLevelExtended, { color: string }> = {
  verde: { color: 'bg-green-100 text-green-800' },
  amarelo: { color: 'bg-yellow-100 text-yellow-800' },
  laranja: { color: 'bg-orange-100 text-orange-800' },
  vermelho: { color: 'bg-red-100 text-red-800' },
  critico: { color: 'bg-red-200 text-red-900' },
}

const warmupPhaseLabels: Record<WarmupPhase, string> = {
  repouso: 'Repouso',
  setup: 'Setup',
  primeiros_contatos: 'Primeiros Contatos',
  expansao: 'Expansão',
  pre_operacao: 'Pré-Operação',
  teste_graduacao: 'Teste de Graduação',
  operacao: 'Operação',
}

export function ChipDetailContent({ chipId }: ChipDetailContentProps) {
  const router = useRouter()
  const [chip, setChip] = useState<ChipFullDetail | null>(null)
  const [metrics, setMetrics] = useState<ChipMetrics | null>(null)
  const [trustHistory, setTrustHistory] = useState<ChipTrustHistory | null>(null)
  const [interactions, setInteractions] = useState<ChipInteractionsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [chipData, metricsData, trustData, interactionsData] = await Promise.all([
        chipsApi.getChipDetail(chipId),
        chipsApi.getChipMetrics(chipId, '24h'),
        chipsApi.getChipTrustHistory(chipId, 30),
        chipsApi.getChipInteractions(chipId, { limit: 20 }),
      ])

      setChip(chipData)
      setMetrics(metricsData)
      setTrustHistory(trustData)
      setInteractions(interactionsData)
      setError(null)
    } catch (err) {
      console.error('Error fetching chip data:', err)
      setError('Não foi possível carregar os dados do chip')
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [chipId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchData()
  }

  const handleActionComplete = () => {
    fetchData()
  }

  if (isLoading) {
    return <ChipDetailSkeleton />
  }

  if (error || !chip) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertTriangle className="mb-4 h-12 w-12 text-gray-400" />
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          {error || 'Chip não encontrado'}
        </h2>
        <p className="mb-4 text-gray-500">Não foi possível carregar os detalhes deste chip.</p>
        <Button variant="outline" onClick={() => router.push('/chips' as Route)}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Voltar para lista
        </Button>
      </div>
    )
  }

  const statusCfg = statusConfig[chip.status]
  const trustCfg = trustLevelConfig[chip.trustLevel]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <nav className="mb-2 text-sm text-gray-500">
            <Link href={'/chips' as Route} className="flex items-center gap-1 hover:text-gray-700">
              <ChevronLeft className="h-4 w-4" />
              Voltar para Pool de Chips
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <Phone className="h-6 w-6 text-gray-400" />
            <h1 className="text-2xl font-bold text-gray-900">{chip.telefone}</h1>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge className={statusCfg.color}>{statusCfg.label}</Badge>
            <Badge className={trustCfg.color}>Trust: {chip.trustScore}</Badge>
            {chip.warmupPhase && (
              <Badge variant="outline">{warmupPhaseLabels[chip.warmupPhase]}</Badge>
            )}
            {chip.hasActiveAlert && (
              <Badge variant="destructive">
                <AlertTriangle className="mr-1 h-3 w-3" />
                Alerta ativo
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="mb-1 flex items-center gap-2 text-gray-500">
              <MessageSquare className="h-4 w-4" />
              <span className="text-sm">Mensagens Hoje</span>
            </div>
            <div className="text-2xl font-bold">
              {chip.messagesToday}{' '}
              <span className="text-sm font-normal text-gray-500">/ {chip.dailyLimit}</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="mb-1 flex items-center gap-2 text-gray-500">
              <Activity className="h-4 w-4" />
              <span className="text-sm">Taxa de Resposta</span>
            </div>
            <div className="text-2xl font-bold">{(chip.responseRate * 100).toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="mb-1 flex items-center gap-2 text-gray-500">
              <TrendingUp className="h-4 w-4" />
              <span className="text-sm">Taxa de Entrega</span>
            </div>
            <div className="text-2xl font-bold">{(chip.deliveryRate * 100).toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="mb-1 flex items-center gap-2 text-gray-500">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm">Erros (24h)</span>
            </div>
            <div className={cn('text-2xl font-bold', chip.errorsLast24h > 5 && 'text-red-600')}>
              {chip.errorsLast24h}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column - charts and metrics */}
        <div className="space-y-6 lg:col-span-2">
          {trustHistory && <ChipTrustChart history={trustHistory} />}
          {metrics && <ChipMetricsCards metrics={metrics} />}
        </div>

        {/* Right column - info and actions */}
        <div className="space-y-6">
          {/* Chip info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Informações do Chip</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow label="ID" value={chip.id} />
              <InfoRow label="DDD" value={chip.ddd} />
              <InfoRow label="Região" value={chip.region} />
              <InfoRow label="Instância" value={chip.instanceName} />
              <InfoRow label="Total Enviadas" value={chip.totalMessagesSent.toLocaleString()} />
              <InfoRow label="Conversas" value={chip.totalConversations.toLocaleString()} />
              <InfoRow label="Bidirecionais" value={chip.totalBidirectional.toLocaleString()} />
              <InfoRow label="Grupos" value={chip.groupsJoined.toLocaleString()} />
              {chip.warmingDay !== undefined && (
                <InfoRow label="Dia de Warmup" value={`Dia ${chip.warmingDay}`} />
              )}
              <InfoRow
                label="Última Atividade"
                value={
                  chip.lastActivityAt
                    ? new Date(chip.lastActivityAt).toLocaleString('pt-BR')
                    : 'Nunca'
                }
              />
              <InfoRow
                label="Criado em"
                value={new Date(chip.createdAt).toLocaleDateString('pt-BR')}
              />
            </CardContent>
          </Card>

          {/* Actions panel */}
          <ChipActionsPanel chip={chip} onActionComplete={handleActionComplete} />
        </div>
      </div>

      {/* Interactions timeline */}
      {interactions && <ChipInteractionsTimeline chipId={chipId} initialData={interactions} />}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  )
}
