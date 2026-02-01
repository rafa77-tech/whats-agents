'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  TrendingUp,
  Clock,
  Activity,
  Download,
  Play,
  Eye,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { KpiCard } from './kpi-card'
import { AnomalyDetailModal } from './anomaly-detail-modal'

interface Anomaly {
  id: string
  tipo: string
  entidade: string
  entidadeId: string
  severidade: 'low' | 'medium' | 'high'
  mensagem: string
  criadaEm: string
  resolvida: boolean
}

interface IntegridadeData {
  kpis: {
    healthScore: number
    conversionRate: number
    timeToFill: number
    componentScores: {
      pressao: number
      friccao: number
      qualidade: number
      spam: number
    }
    recommendations: string[]
  }
  anomalias: {
    abertas: number
    resolvidas: number
    total: number
  }
  violacoes: number
  ultimaAuditoria: string | null
  anomaliasList: Anomaly[]
}

export function IntegridadePageContent() {
  const [data, setData] = useState<IntegridadeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null)
  const [runningAudit, setRunningAudit] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  const fetchData = useCallback(async () => {
    try {
      setError(null)

      // Fetch integridade data from backend
      const [kpisRes, anomaliasRes] = await Promise.all([
        fetch('/api/integridade/kpis').catch(() => null),
        fetch('/api/integridade/anomalias?limit=20').catch(() => null),
      ])

      // Parse KPIs - backend returns nested structure
      let kpis = {
        healthScore: 0,
        conversionRate: 0,
        timeToFill: 0,
        componentScores: { pressao: 0, friccao: 0, qualidade: 0, spam: 0 },
        recommendations: [] as string[],
      }
      if (kpisRes?.ok) {
        const kpisData = await kpisRes.json()
        // Backend structure: { kpis: { health_score: { score, component_scores }, conversion_rate: { value }, time_to_fill: { time_to_fill_full: { avg_hours } } } }
        const kpisNested = kpisData.kpis || kpisData
        kpis = {
          healthScore: kpisNested.health_score?.score ?? kpisData.health_score ?? 0,
          conversionRate: kpisNested.conversion_rate?.value ?? kpisData.conversion_rate ?? 0,
          timeToFill: kpisNested.time_to_fill?.time_to_fill_full?.avg_hours ?? kpisData.time_to_fill ?? 0,
          componentScores: {
            pressao: kpisNested.health_score?.component_scores?.pressao ?? 0,
            friccao: kpisNested.health_score?.component_scores?.friccao ?? 0,
            qualidade: kpisNested.health_score?.component_scores?.qualidade ?? 0,
            spam: kpisNested.health_score?.component_scores?.spam ?? 0,
          },
          recommendations: kpisNested.health_score?.recommendations || [],
        }
      }

      // Parse anomalias - backend returns "anomalies" not "anomalias"
      let anomaliasList: Anomaly[] = []
      let anomalias = { abertas: 0, resolvidas: 0, total: 0 }
      if (anomaliasRes?.ok) {
        const anomaliasData = await anomaliasRes.json()
        // Backend uses "anomalies" key
        const rawAnomalies = anomaliasData.anomalies || anomaliasData.anomalias || []
        anomaliasList = rawAnomalies.map((a: Record<string, unknown>) => ({
          id: a.id,
          tipo: a.tipo || a.type,
          entidade: a.entidade || a.entity,
          entidadeId: a.entidade_id || a.entity_id,
          severidade: a.severidade || a.severity,
          mensagem: a.mensagem || a.message,
          criadaEm: a.criada_em || a.created_at,
          resolvida: a.resolvida || a.resolved || false,
        }))
        // Use summary from backend if available
        const summary = anomaliasData.summary || {}
        anomalias = {
          abertas: summary.by_severity?.warning + summary.by_severity?.critical || anomaliasList.filter((a) => !a.resolvida).length,
          resolvidas: anomaliasList.filter((a) => a.resolvida).length,
          total: summary.total || anomaliasList.length,
        }
      }

      setData({
        kpis,
        anomalias,
        violacoes: anomalias.abertas, // Use abertas as violacoes count
        ultimaAuditoria: new Date().toISOString(), // Mark as "just checked"
        anomaliasList,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRunAudit = async () => {
    setRunningAudit(true)
    try {
      await fetch('/api/integridade/reconciliacao', { method: 'POST' })
      await fetchData()
    } catch {
      // Ignore errors
    } finally {
      setRunningAudit(false)
    }
  }

  const handleResolveAnomaly = async (anomalyId: string, notas: string) => {
    try {
      await fetch(`/api/integridade/anomalias/${anomalyId}/resolver`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notas, usuario: 'dashboard' }),
      })
      setSelectedAnomaly(null)
      await fetchData()
    } catch {
      // Ignore errors
    }
  }

  const getSeverityBadge = (severidade: string) => {
    switch (severidade) {
      case 'high':
        return <Badge className="bg-red-100 text-red-800">Alta</Badge>
      case 'medium':
        return <Badge className="bg-yellow-100 text-yellow-800">Media</Badge>
      default:
        return <Badge className="bg-blue-100 text-blue-800">Baixa</Badge>
    }
  }

  if (loading && !data) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-2 text-sm text-gray-500">Carregando dados de integridade...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-8 w-8 text-red-400" />
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <Button onClick={fetchData} variant="outline" className="mt-4">
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
          <h1 className="text-2xl font-bold text-gray-900">Integridade dos Dados</h1>
          <p className="text-gray-500">Monitoramento de anomalias e saude do funil</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={fetchData} variant="outline" size="sm" disabled={loading}>
            <RefreshCw className={cn('mr-2 h-4 w-4', loading && 'animate-spin')} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard
          title="Health Score"
          value={data?.kpis.healthScore || 0}
          suffix="/100"
          icon={Activity}
          status={
            (data?.kpis.healthScore || 0) >= 80
              ? 'good'
              : (data?.kpis.healthScore || 0) >= 60
                ? 'warn'
                : 'bad'
          }
        />
        <KpiCard
          title="Taxa de Conversao"
          value={data?.kpis.conversionRate || 0}
          suffix="%"
          icon={TrendingUp}
          status={
            (data?.kpis.conversionRate || 0) >= 30
              ? 'good'
              : (data?.kpis.conversionRate || 0) >= 20
                ? 'warn'
                : 'bad'
          }
        />
        <KpiCard
          title="Time-to-Fill"
          value={data?.kpis.timeToFill || 0}
          suffix="h"
          icon={Clock}
          status={
            (data?.kpis.timeToFill || 0) <= 4
              ? 'good'
              : (data?.kpis.timeToFill || 0) <= 8
                ? 'warn'
                : 'bad'
          }
        />
      </div>

      {/* Counters */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-gray-500">Anomalias Abertas</p>
              <p className="text-2xl font-bold text-yellow-600">{data?.anomalias.abertas || 0}</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-yellow-400" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-gray-500">Violacoes</p>
              <p className="text-2xl font-bold text-red-600">{data?.violacoes || 0}</p>
            </div>
            <XCircle className="h-8 w-8 text-red-400" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-gray-500">Ultima Auditoria</p>
              <p className="text-sm font-medium text-gray-700">
                {data?.ultimaAuditoria ? new Date(data.ultimaAuditoria).toLocaleString('pt-BR') : 'Nunca'}
              </p>
            </div>
            <Button onClick={handleRunAudit} size="sm" disabled={runningAudit}>
              {runningAudit ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Anomalias</TabsTrigger>
          <TabsTrigger value="kpis">KPIs Detalhados</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Lista de Anomalias</CardTitle>
                  <CardDescription>
                    {data?.anomalias.abertas || 0} abertas de {data?.anomalias.total || 0} total
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  <Download className="mr-2 h-4 w-4" />
                  Exportar CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {data?.anomaliasList && data.anomaliasList.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Entidade</TableHead>
                      <TableHead>Severidade</TableHead>
                      <TableHead>Criada</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Acoes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.anomaliasList.map((anomaly) => (
                      <TableRow key={anomaly.id}>
                        <TableCell className="font-medium">{anomaly.tipo}</TableCell>
                        <TableCell>
                          <code className="text-xs">{anomaly.entidadeId}</code>
                        </TableCell>
                        <TableCell>{getSeverityBadge(anomaly.severidade)}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(anomaly.criadaEm).toLocaleDateString('pt-BR')}
                        </TableCell>
                        <TableCell>
                          {anomaly.resolvida ? (
                            <Badge className="bg-green-100 text-green-800">Resolvida</Badge>
                          ) : (
                            <Badge className="bg-yellow-100 text-yellow-800">Aberta</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedAnomaly(anomaly)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="py-8 text-center text-gray-500">
                  <CheckCircle2 className="mx-auto h-8 w-8 text-green-400" />
                  <p className="mt-2">Nenhuma anomalia encontrada</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="kpis">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">KPIs Detalhados</CardTitle>
              <CardDescription>Breakdown dos indicadores de saude</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Health Score Components */}
                <div>
                  <h3 className="mb-3 text-sm font-medium">Health Score: {data?.kpis.healthScore.toFixed(1)}/100</h3>
                  <div className="space-y-2">
                    {[
                      { label: 'Pressao de Vagas', key: 'pressao' as const },
                      { label: 'Friccao no Funil', key: 'friccao' as const },
                      { label: 'Qualidade Respostas', key: 'qualidade' as const },
                      { label: 'Score de Spam', key: 'spam' as const },
                    ].map(({ label, key }) => {
                      const value = data?.kpis.componentScores[key] || 0
                      // Convert component score to percentage (lower is better for these metrics)
                      const percentage = Math.max(0, Math.min(100, 100 - value * 10))
                      const color = percentage >= 80 ? 'bg-green-500' : percentage >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                      return (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">{label}</span>
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                              <div className={cn('h-full', color)} style={{ width: `${percentage}%` }} />
                            </div>
                            <span className="text-sm font-medium">{percentage.toFixed(0)}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Recommendations */}
                <div>
                  <h3 className="mb-3 text-sm font-medium">Recomendacoes</h3>
                  <div className="space-y-2">
                    {data?.kpis.recommendations && data.kpis.recommendations.length > 0 ? (
                      data.kpis.recommendations.map((rec, idx) => (
                        <div key={idx} className="flex items-start gap-2 rounded-lg bg-yellow-50 p-3">
                          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                          <p className="text-sm text-yellow-800">{rec}</p>
                        </div>
                      ))
                    ) : (
                      <div className="flex items-start gap-2 rounded-lg bg-green-50 p-3">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
                        <p className="text-sm text-green-800">
                          Nenhuma recomendacao no momento. Sistema saudavel!
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Anomaly Detail Modal */}
      {selectedAnomaly && (
        <AnomalyDetailModal
          anomaly={selectedAnomaly}
          onClose={() => setSelectedAnomaly(null)}
          onResolve={handleResolveAnomaly}
        />
      )}
    </div>
  )
}
