/**
 * Warmup Page Content - Sprint 42
 *
 * Conteúdo da página de atividades de warmup.
 * Renomeado de SchedulerPageContent (Sprint 42).
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { ChevronLeft, RefreshCw, Flame, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import {
  ScheduledActivity,
  SchedulerStats,
  ActivityStatus,
  ScheduledActivityType,
} from '@/types/chips'

const activityTypeLabels: Record<ScheduledActivityType, string> = {
  CONVERSA_PAR: 'Conversa Par',
  MARCAR_LIDO: 'Marcar Lido',
  ENTRAR_GRUPO: 'Entrar Grupo',
  ENVIAR_MIDIA: 'Enviar Midia',
  MENSAGEM_GRUPO: 'Mensagem Grupo',
  ATUALIZAR_PERFIL: 'Atualizar Perfil',
}

const statusConfig: Record<ActivityStatus, { label: string; color: string; icon: typeof Clock }> = {
  planejada: { label: 'Planejada', color: 'bg-blue-100 text-blue-800', icon: Clock },
  executada: { label: 'Executada', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  falhou: { label: 'Falhou', color: 'bg-red-100 text-red-800', icon: XCircle },
  cancelada: { label: 'Cancelada', color: 'bg-gray-100 text-gray-800', icon: XCircle },
}

export function WarmupPageContent() {
  const [activities, setActivities] = useState<ScheduledActivity[]>([])
  const [stats, setStats] = useState<SchedulerStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

  const fetchData = useCallback(async () => {
    try {
      const params = selectedDate ? { date: selectedDate, limit: 50 } : { limit: 50 }
      const [activitiesData, statsData] = await Promise.all([
        chipsApi.getWarmupActivities(params),
        chipsApi.getWarmupStats(selectedDate || undefined),
      ])
      setActivities(activitiesData)
      setStats(statsData)
    } catch (error) {
      console.error('Error fetching warmup data:', error)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [selectedDate])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchData()
  }

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 w-48 rounded bg-gray-200" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded bg-gray-200" />
          ))}
        </div>
        <div className="h-96 rounded bg-gray-200" />
      </div>
    )
  }

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
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Flame className="h-6 w-6" />
            Warmup de Atividades
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Visualize e monitore as atividades de warmup agendadas
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-md border border-gray-200 px-3 py-2 text-sm"
          />
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="p-4">
              <div className="mb-1 text-sm text-gray-600">Planejadas</div>
              <div className="text-2xl font-bold text-blue-600">{stats.totalPlanned}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="mb-1 text-sm text-gray-600">Executadas</div>
              <div className="text-2xl font-bold text-green-600">{stats.totalExecuted}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="mb-1 text-sm text-gray-600">Falhas</div>
              <div className="text-2xl font-bold text-red-600">{stats.totalFailed}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="mb-1 text-sm text-gray-600">Taxa de Sucesso</div>
              <div className="text-2xl font-bold">
                {stats.totalExecuted + stats.totalFailed > 0
                  ? (
                      (stats.totalExecuted / (stats.totalExecuted + stats.totalFailed)) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Activities by type */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Atividades por Tipo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
              {(Object.keys(stats.byType) as ScheduledActivityType[]).map((type) => {
                const data = stats.byType[type]
                return (
                  <div key={type} className="rounded-lg bg-gray-50 p-3">
                    <div className="mb-1 text-xs text-gray-500">{activityTypeLabels[type]}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-semibold">{data.executed}</span>
                      <span className="text-xs text-gray-400">/ {data.planned}</span>
                    </div>
                    {data.failed > 0 && (
                      <div className="mt-1 text-xs text-red-500">{data.failed} falhas</div>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Activities list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Atividades do Dia</CardTitle>
        </CardHeader>
        <CardContent>
          {activities.length === 0 ? (
            <p className="py-8 text-center text-gray-500">
              Nenhuma atividade agendada para esta data.
            </p>
          ) : (
            <div className="space-y-2">
              {activities.map((activity) => {
                const config = statusConfig[activity.status]
                const Icon = config.icon
                return (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between rounded-lg bg-gray-50 p-3"
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={cn(
                          'h-4 w-4',
                          activity.status === 'executada'
                            ? 'text-green-500'
                            : activity.status === 'falhou'
                              ? 'text-red-500'
                              : 'text-blue-500'
                        )}
                      />
                      <div>
                        <div className="text-sm font-medium">
                          {activityTypeLabels[activity.type]}
                        </div>
                        <div className="text-xs text-gray-500">
                          {activity.chipTelefone} •{' '}
                          {new Date(activity.scheduledAt).toLocaleTimeString('pt-BR', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={config.color}>{config.label}</Badge>
                      {activity.errorMessage && (
                        <span className="max-w-32 truncate text-xs text-red-500">
                          {activity.errorMessage}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
