/**
 * Alerts Page Content - Sprint 36
 *
 * Conteúdo principal da página de alertas.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { ChevronLeft, RefreshCw, AlertTriangle, CheckCircle, Filter } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { AlertsPageSkeleton } from './alerts-page-skeleton'
import { AlertCard } from './alert-card'
import {
  ChipAlert,
  ChipAlertsListResponse,
  ChipAlertsListParams,
  ChipAlertSeverity,
  ChipAlertType,
} from '@/types/chips'

const severityOptions: { value: ChipAlertSeverity; label: string }[] = [
  { value: 'critico', label: 'Crítico' },
  { value: 'alerta', label: 'Alerta' },
  { value: 'atencao', label: 'Atenção' },
  { value: 'info', label: 'Info' },
]

const typeOptions: { value: ChipAlertType; label: string }[] = [
  { value: 'TRUST_CAINDO', label: 'Trust Caindo' },
  { value: 'TAXA_BLOCK_ALTA', label: 'Taxa de Block Alta' },
  { value: 'ERROS_FREQUENTES', label: 'Erros Frequentes' },
  { value: 'DELIVERY_BAIXO', label: 'Delivery Baixo' },
  { value: 'RESPOSTA_BAIXA', label: 'Resposta Baixa' },
  { value: 'DESCONEXAO', label: 'Desconexão' },
  { value: 'LIMITE_PROXIMO', label: 'Limite Próximo' },
  { value: 'FASE_ESTAGNADA', label: 'Fase Estagnada' },
  { value: 'QUALIDADE_META', label: 'Qualidade Meta' },
  { value: 'COMPORTAMENTO_ANOMALO', label: 'Comportamento Anômalo' },
]

const severityConfig: Record<ChipAlertSeverity, { color: string; bgColor: string }> = {
  critico: { color: 'text-status-error-foreground', bgColor: 'bg-status-error' },
  alerta: { color: 'text-status-warning-foreground', bgColor: 'bg-status-warning' },
  atencao: { color: 'text-status-warning-foreground', bgColor: 'bg-status-warning' },
  info: { color: 'text-status-info-foreground', bgColor: 'bg-status-info' },
}

export function AlertsPageContent() {
  const [alerts, setAlerts] = useState<ChipAlert[]>([])
  const [response, setResponse] = useState<ChipAlertsListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Partial<ChipAlertsListParams>>({
    resolved: false,
  })

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await chipsApi.listAlerts({
        page,
        pageSize: 20,
        ...filters,
      })
      setAlerts(data.alerts)
      setResponse(data)
    } catch (error) {
      console.error('Error fetching alerts:', error)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [page, filters])

  useEffect(() => {
    fetchAlerts()
  }, [fetchAlerts])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchAlerts()
  }

  const handleSeverityChange = (severity: string) => {
    const { severity: _severity, ...rest } = filters
    if (severity === 'all') {
      setFilters(rest)
    } else {
      setFilters({ ...rest, severity: severity as ChipAlertSeverity })
    }
    setPage(1)
  }

  const handleTypeChange = (type: string) => {
    const { type: _type, ...rest } = filters
    if (type === 'all') {
      setFilters(rest)
    } else {
      setFilters({ ...rest, type: type as ChipAlertType })
    }
    setPage(1)
  }

  const handleResolvedChange = (resolved: string) => {
    const { resolved: _resolved, ...rest } = filters
    if (resolved === 'all') {
      setFilters(rest)
    } else {
      setFilters({ ...rest, resolved: resolved === 'resolved' })
    }
    setPage(1)
  }

  const handleAlertResolved = () => {
    fetchAlerts()
  }

  if (isLoading) {
    return <AlertsPageSkeleton />
  }

  const countBySeverity = response?.countBySeverity || {
    critico: 0,
    alerta: 0,
    atencao: 0,
    info: 0,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <nav className="mb-2 text-sm text-muted-foreground">
            <Link
              href={'/chips' as Route}
              className="flex items-center gap-1 hover:text-foreground"
            >
              <ChevronLeft className="h-4 w-4" />
              Voltar para Pool de Chips
            </Link>
          </nav>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-foreground">
            <AlertTriangle className="h-6 w-6" />
            Alertas
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Gerencie alertas do pool de chips</p>
        </div>

        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} />
          Atualizar
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {severityOptions.map((severity) => {
          const count = countBySeverity[severity.value] || 0
          const config = severityConfig[severity.value]
          return (
            <Card
              key={severity.value}
              className={cn(
                'cursor-pointer transition-colors hover:border-border/80',
                filters.severity === severity.value && 'border-accent-foreground/40'
              )}
              onClick={() =>
                handleSeverityChange(filters.severity === severity.value ? 'all' : severity.value)
              }
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{severity.label}</span>
                  <Badge className={cn(config.bgColor, config.color)}>{count}</Badge>
                </div>
                <div className={cn('mt-1 text-2xl font-bold', config.color)}>{count}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />

        <Select value={(filters.severity as string) || 'all'} onValueChange={handleSeverityChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severidade" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas severidades</SelectItem>
            {severityOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={(filters.type as string) || 'all'} onValueChange={handleTypeChange}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os tipos</SelectItem>
            {typeOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={
            filters.resolved === undefined ? 'all' : filters.resolved ? 'resolved' : 'unresolved'
          }
          onValueChange={handleResolvedChange}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="unresolved">Não resolvidos</SelectItem>
            <SelectItem value="resolved">Resolvidos</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Alerts list */}
      {alerts.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <CheckCircle className="mx-auto mb-4 h-12 w-12 text-status-success-solid" />
            <h3 className="mb-2 text-lg font-semibold text-foreground">Nenhum alerta encontrado</h3>
            <p className="text-muted-foreground">
              {filters.resolved === false
                ? 'Não há alertas pendentes. Ótimo trabalho!'
                : 'Nenhum alerta corresponde aos filtros selecionados.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} onResolved={handleAlertResolved} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {response && response.total > 20 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Mostrando {alerts.length} de {response.total} alertas
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!response.hasMore}
              onClick={() => setPage(page + 1)}
            >
              Próxima
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
