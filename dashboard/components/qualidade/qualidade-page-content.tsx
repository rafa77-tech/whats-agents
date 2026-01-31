'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  RefreshCw,
  Loader2,
  XCircle,
  Star,
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
  ClipboardList,
  Lightbulb,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { QualityMetricCard } from './quality-metric-card'
import { ConversationsList } from './conversations-list'
import { SuggestionsList } from './suggestions-list'

interface QualityMetrics {
  avaliadas: number
  pendentes: number
  scoreMedio: number
  validacaoTaxa: number
  validacaoFalhas: number
  padroesViolados: Array<{ padrao: string; count: number }>
}

export function QualidadePageContent() {
  const [metrics, setMetrics] = useState<QualityMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')

  const fetchMetrics = useCallback(async () => {
    try {
      setError(null)

      const [performanceRes, validacaoRes] = await Promise.all([
        fetch('/api/admin/metricas/performance').catch(() => null),
        fetch('/api/admin/validacao/metricas').catch(() => null),
      ])

      let performanceData = null
      if (performanceRes?.ok) {
        performanceData = await performanceRes.json()
      }

      let validacaoData = null
      if (validacaoRes?.ok) {
        validacaoData = await validacaoRes.json()
      }

      setMetrics({
        avaliadas: performanceData?.avaliadas || 0,
        pendentes: performanceData?.pendentes || 0,
        scoreMedio: performanceData?.score_medio || 0,
        validacaoTaxa: validacaoData?.taxa_sucesso || 98,
        validacaoFalhas: validacaoData?.falhas || 0,
        padroesViolados: validacaoData?.padroes_violados || [],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics])

  if (loading && !metrics) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-2 text-sm text-gray-500">Carregando metricas...</p>
        </div>
      </div>
    )
  }

  if (error && !metrics) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-8 w-8 text-red-400" />
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <Button onClick={fetchMetrics} variant="outline" className="mt-4">
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
          <h1 className="text-2xl font-bold text-gray-900">Qualidade das Conversas</h1>
          <p className="text-gray-500">Avaliacao e gestao de qualidade das respostas</p>
        </div>
        <Button onClick={fetchMetrics} variant="outline" size="sm" disabled={loading}>
          <RefreshCw className={cn('mr-2 h-4 w-4', loading && 'animate-spin')} />
          Atualizar
        </Button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <QualityMetricCard
          title="Avaliadas"
          value={metrics?.avaliadas || 0}
          icon={CheckCircle2}
          color="green"
        />
        <QualityMetricCard
          title="Pendentes"
          value={metrics?.pendentes || 0}
          icon={ClipboardList}
          color="yellow"
        />
        <QualityMetricCard
          title="Score Medio"
          value={metrics?.scoreMedio || 0}
          suffix="/5"
          icon={Star}
          color="blue"
        />
        <QualityMetricCard
          title="Validacoes"
          value={metrics?.validacaoTaxa || 0}
          suffix="%"
          icon={CheckCircle2}
          color="green"
        />
      </div>

      {/* Work Queues */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <p className="text-sm text-gray-500">Conversas para Avaliar</p>
              <p className="text-2xl font-bold">{metrics?.pendentes || 0} novas</p>
            </div>
            <div className="flex items-center gap-3">
              <MessageSquare className="h-8 w-8 text-blue-400" />
              <Button
                size="sm"
                onClick={() => setActiveTab('conversas')}
                disabled={(metrics?.pendentes || 0) === 0}
              >
                Iniciar Avaliacao
              </Button>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-6">
            <div>
              <p className="text-sm text-gray-500">Sugestoes Pendentes</p>
              <p className="text-2xl font-bold">- aguardando</p>
            </div>
            <div className="flex items-center gap-3">
              <Lightbulb className="h-8 w-8 text-yellow-400" />
              <Button size="sm" variant="outline" onClick={() => setActiveTab('sugestoes')}>
                Ver Sugestoes
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Validator Summary */}
      {metrics && metrics.padroesViolados.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Validador de Output</CardTitle>
            <CardDescription>
              {metrics.validacaoFalhas} falhas hoje ({(100 - metrics.validacaoTaxa).toFixed(1)}%)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {metrics.padroesViolados.slice(0, 5).map((p) => (
                <div
                  key={p.padrao}
                  className="flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-sm"
                >
                  <AlertTriangle className="h-3 w-3 text-red-600" />
                  <span className="text-red-700">
                    {p.padrao} ({p.count})
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Visao Geral</TabsTrigger>
          <TabsTrigger value="conversas">Conversas</TabsTrigger>
          <TabsTrigger value="sugestoes">Sugestoes</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resumo de Qualidade</CardTitle>
              <CardDescription>Visao geral das metricas de qualidade</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <div className="rounded-lg bg-gray-50 p-4 text-center">
                    <p className="text-xs text-gray-500">Naturalidade</p>
                    <p className="text-xl font-bold">-</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4 text-center">
                    <p className="text-xs text-gray-500">Persona</p>
                    <p className="text-xl font-bold">-</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4 text-center">
                    <p className="text-xs text-gray-500">Objetivo</p>
                    <p className="text-xl font-bold">-</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4 text-center">
                    <p className="text-xs text-gray-500">Satisfacao</p>
                    <p className="text-xl font-bold">-</p>
                  </div>
                </div>
                <p className="text-center text-sm text-gray-500">
                  Avalie conversas para gerar metricas detalhadas
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="conversas">
          <ConversationsList />
        </TabsContent>

        <TabsContent value="sugestoes">
          <SuggestionsList />
        </TabsContent>
      </Tabs>
    </div>
  )
}
