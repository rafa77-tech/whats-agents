'use client'

import { useState } from 'react'
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
import {
  useIntegridadeData,
  getHealthScoreStatus,
  getConversionRateStatus,
  getTimeToFillStatus,
  getAnomalySeverityColors,
  getAnomalySeverityLabel,
  getAnomalyResolutionColors,
  getAnomalyResolutionLabel,
  getProgressColor,
  convertComponentScoreToPercentage,
  formatDateBR,
  formatDateTimeBR,
  HEALTH_SCORE_COMPONENTS,
} from '@/lib/integridade'
import type { Anomaly } from '@/lib/integridade'

export function IntegridadePageContent() {
  const { data, loading, error, fetchData, runAudit, resolveAnomaly, runningAudit } =
    useIntegridadeData()
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null)
  const [activeTab, setActiveTab] = useState('overview')

  const handleResolveAnomaly = async (anomalyId: string, notas: string) => {
    await resolveAnomaly(anomalyId, notas)
    setSelectedAnomaly(null)
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

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-red-800">
          <AlertTriangle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard
          title="Health Score"
          value={data?.kpis.healthScore || 0}
          suffix="/100"
          icon={Activity}
          status={getHealthScoreStatus(data?.kpis.healthScore || 0)}
        />
        <KpiCard
          title="Taxa de Conversao"
          value={data?.kpis.conversionRate || 0}
          suffix="%"
          icon={TrendingUp}
          status={getConversionRateStatus(data?.kpis.conversionRate || 0)}
        />
        <KpiCard
          title="Time-to-Fill"
          value={data?.kpis.timeToFill || 0}
          suffix="h"
          icon={Clock}
          status={getTimeToFillStatus(data?.kpis.timeToFill || 0)}
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
                {data?.ultimaAuditoria ? formatDateTimeBR(data.ultimaAuditoria) : 'Nunca'}
              </p>
            </div>
            <Button onClick={runAudit} size="sm" disabled={runningAudit}>
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
                    {data.anomaliasList.map((anomaly) => {
                      const severityColors = getAnomalySeverityColors(anomaly.severidade)
                      const resolutionColors = getAnomalyResolutionColors(anomaly.resolvida)
                      return (
                        <TableRow key={anomaly.id}>
                          <TableCell className="font-medium">{anomaly.tipo}</TableCell>
                          <TableCell>
                            <code className="text-xs">{anomaly.entidadeId}</code>
                          </TableCell>
                          <TableCell>
                            <Badge className={severityColors.badge}>
                              {getAnomalySeverityLabel(anomaly.severidade)}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-gray-500">
                            {formatDateBR(anomaly.criadaEm)}
                          </TableCell>
                          <TableCell>
                            <Badge className={`${resolutionColors.bg} ${resolutionColors.text}`}>
                              {getAnomalyResolutionLabel(anomaly.resolvida)}
                            </Badge>
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
                      )
                    })}
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
                  <h3 className="mb-3 text-sm font-medium">
                    Health Score: {data?.kpis.healthScore.toFixed(1)}/100
                  </h3>
                  <div className="space-y-2">
                    {HEALTH_SCORE_COMPONENTS.map(({ label, key }) => {
                      const value = data?.kpis.componentScores[key] || 0
                      const percentage = convertComponentScoreToPercentage(value)
                      const color = getProgressColor(percentage)
                      return (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">{label}</span>
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                              <div
                                className={cn('h-full', color)}
                                style={{ width: `${percentage}%` }}
                              />
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
                        <div
                          key={idx}
                          className="flex items-start gap-2 rounded-lg bg-yellow-50 p-3"
                        >
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
