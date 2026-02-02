'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RefreshCw, AlertTriangle, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { HealthGauge } from './health-gauge'
import { CircuitBreakersPanel } from './circuit-breakers-panel'
import { AlertsPanel } from './alerts-panel'
import { RateLimitPanel } from './rate-limit-panel'
import { QueueStatusPanel } from './queue-status-panel'

interface HealthData {
  score: number
  status: 'healthy' | 'degraded' | 'critical'
  alerts: Array<{
    id: string
    tipo: string
    severity: 'info' | 'warn' | 'critical'
    message: string
    source: string
  }>
  circuits: Array<{
    name: string
    state: 'CLOSED' | 'HALF_OPEN' | 'OPEN'
    failures: number
    threshold: number
  }>
  services: Array<{
    name: string
    status: 'ok' | 'warn' | 'error'
  }>
  rateLimit: {
    hourly: { used: number; limit: number }
    daily: { used: number; limit: number }
  }
  queue: {
    pendentes: number
    processando: number
    processadasPorHora?: number
    tempoMedioMs?: number | null
  }
}

const REFRESH_INTERVALS = [
  { label: '15s', value: 15000 },
  { label: '30s', value: 30000 },
  { label: '60s', value: 60000 },
  { label: 'Off', value: 0 },
]

export function HealthPageContent() {
  const [data, setData] = useState<HealthData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshInterval, setRefreshInterval] = useState(30000)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchHealthData = useCallback(async () => {
    try {
      setError(null)

      // Fetch data from multiple endpoints in parallel
      const [monitorRes, guardrailsRes, rateLimitRes, servicesRes, queueRes] = await Promise.all([
        fetch('/api/dashboard/monitor'),
        fetch('/api/guardrails/status').catch(() => null),
        fetch('/api/health/rate-limit').catch(() => null),
        fetch('/api/health/services').catch(() => null),
        fetch('/api/health/queue').catch(() => null),
      ])

      if (!monitorRes.ok) {
        throw new Error('Falha ao carregar dados de saude')
      }

      const monitorData = await monitorRes.json()

      // Parse guardrails data if available
      let guardrailsData = null
      if (guardrailsRes?.ok) {
        guardrailsData = await guardrailsRes.json()
      }

      // Parse rate limit data
      let rateLimitData = null
      if (rateLimitRes?.ok) {
        rateLimitData = await rateLimitRes.json()
      }

      // Parse services data
      let servicesData = null
      if (servicesRes?.ok) {
        servicesData = await servicesRes.json()
      }

      // Parse queue data
      let queueData = null
      if (queueRes?.ok) {
        queueData = await queueRes.json()
      }

      // Build services from real API or fallback to calculated
      const services = servicesData?.services || [
        {
          name: 'WhatsApp',
          status:
            monitorData.systemHealth?.checks?.connectivity?.score === 100
              ? 'ok'
              : monitorData.systemHealth?.checks?.connectivity?.score > 50
                ? 'warn'
                : 'error',
        },
        { name: 'Redis', status: 'warn' },
        { name: 'Supabase', status: 'ok' },
        { name: 'LLM', status: 'ok' },
      ]

      // Add Fila service based on queue data or monitor
      const filaScore = monitorData.systemHealth?.checks?.fila?.score || 100
      services.push({
        name: 'Fila',
        status: filaScore > 80 ? 'ok' : filaScore > 50 ? 'warn' : 'error',
      })

      // Map monitor data to health data
      const healthData: HealthData = {
        score: monitorData.systemHealth?.score || 0,
        status: monitorData.systemHealth?.status || 'degraded',
        alerts: [
          ...(monitorData.alerts?.criticalStale || []).map((job: string) => ({
            id: `stale-${job}`,
            tipo: 'job_stale',
            severity: 'critical' as const,
            message: `Job ${job} esta stale (excedeu SLA)`,
            source: 'scheduler',
          })),
          ...(monitorData.alerts?.jobsWithErrors || []).map((job: string) => ({
            id: `error-${job}`,
            tipo: 'job_error',
            severity: 'warn' as const,
            message: `Job ${job} teve erros nas ultimas 24h`,
            source: 'scheduler',
          })),
        ],
        circuits: guardrailsData?.circuits || [
          { name: 'evolution', state: 'CLOSED', failures: 0, threshold: 5 },
          { name: 'claude', state: 'CLOSED', failures: 0, threshold: 5 },
          { name: 'supabase', state: 'CLOSED', failures: 0, threshold: 5 },
        ],
        services,
        rateLimit: rateLimitData?.rate_limit || {
          hourly: { used: 0, limit: 20 },
          daily: { used: 0, limit: 100 },
        },
        queue: {
          pendentes: queueData?.queue?.pendentes || 0,
          processando: queueData?.queue?.processando || 0,
          processadasPorHora: queueData?.queue?.processadasPorHora,
          tempoMedioMs: queueData?.queue?.tempoMedioMs,
        },
      }

      setData(healthData)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealthData()
  }, [fetchHealthData])

  useEffect(() => {
    if (refreshInterval > 0) {
      const interval = setInterval(fetchHealthData, refreshInterval)
      return () => clearInterval(interval)
    }
    return undefined
  }, [refreshInterval, fetchHealthData])

  if (loading && !data) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-2 text-sm text-gray-500">Carregando dados de saude...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-8 w-8 text-status-error-solid" />
          <p className="mt-2 text-sm text-status-error-solid">{error}</p>
          <Button onClick={fetchHealthData} variant="outline" className="mt-4">
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Health Center</h1>
          <p className="text-gray-500">Monitoramento consolidado de saude do sistema</p>
        </div>
        <div className="flex items-center gap-4">
          {/* Refresh interval selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Auto-refresh:</span>
            <div className="flex rounded-lg border border-gray-200">
              {REFRESH_INTERVALS.map((interval) => (
                <button
                  key={interval.value}
                  onClick={() => setRefreshInterval(interval.value)}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium transition-colors',
                    refreshInterval === interval.value
                      ? 'bg-revoluna-500 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  )}
                >
                  {interval.label}
                </button>
              ))}
            </div>
          </div>
          <Button onClick={fetchHealthData} variant="outline" size="sm" disabled={loading}>
            <RefreshCw className={cn('mr-2 h-4 w-4', loading && 'animate-spin')} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Health Score */}
      <Card className="border-2 border-gray-100">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center">
            <HealthGauge score={data?.score || 0} status={data?.status || 'degraded'} />
            <div className="mt-4 text-center">
              <Badge
                className={cn(
                  'text-sm',
                  data?.status === 'healthy' && 'bg-status-success text-status-success-foreground',
                  data?.status === 'degraded' && 'bg-status-warning text-status-warning-foreground',
                  data?.status === 'critical' && 'bg-status-error text-status-error-foreground'
                )}
              >
                {data?.status === 'healthy' && 'HEALTHY'}
                {data?.status === 'degraded' && 'DEGRADED'}
                {data?.status === 'critical' && 'CRITICAL'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Services Status */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Status dos Servicos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {data?.services.map((service) => (
              <div
                key={service.name}
                className={cn(
                  'flex items-center gap-2 rounded-lg px-4 py-2',
                  service.status === 'ok' && 'bg-status-success/20',
                  service.status === 'warn' && 'bg-status-warning/20',
                  service.status === 'error' && 'bg-status-error/20'
                )}
              >
                {service.status === 'ok' && <CheckCircle2 className="h-4 w-4 text-status-success-foreground" />}
                {service.status === 'warn' && <AlertTriangle className="h-4 w-4 text-status-warning-foreground" />}
                {service.status === 'error' && <XCircle className="h-4 w-4 text-status-error-foreground" />}
                <span
                  className={cn(
                    'text-sm font-medium',
                    service.status === 'ok' && 'text-status-success-foreground',
                    service.status === 'warn' && 'text-status-warning-foreground',
                    service.status === 'error' && 'text-status-error-foreground'
                  )}
                >
                  {service.name}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Alerts */}
      {data && data.alerts.length > 0 && <AlertsPanel alerts={data.alerts} />}

      {/* Circuit Breakers & Rate Limit */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CircuitBreakersPanel circuits={data?.circuits || []} onReset={fetchHealthData} />
        <RateLimitPanel rateLimit={data?.rateLimit} />
      </div>

      {/* Queue Status */}
      <QueueStatusPanel queue={data?.queue} />

      {/* Last Updated */}
      {lastUpdated && (
        <p className="text-center text-xs text-gray-400">
          Ultima atualizacao: {lastUpdated.toLocaleTimeString('pt-BR')}
        </p>
      )}
    </div>
  )
}
