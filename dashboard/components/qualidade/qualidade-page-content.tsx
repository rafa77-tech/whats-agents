'use client'

import { useState } from 'react'
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
import { useQualidadeMetrics, calculateFailureRate, MAX_PATTERNS_DISPLAYED } from '@/lib/qualidade'
import { QualityMetricCard } from './quality-metric-card'
import { ConversationsList } from './conversations-list'
import { SuggestionsList } from './suggestions-list'

export function QualidadePageContent() {
  const { metrics, loading, error, refresh } = useQualidadeMetrics()
  const [activeTab, setActiveTab] = useState('overview')

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
          <XCircle className="mx-auto h-8 w-8 text-status-error-solid" />
          <p className="mt-2 text-sm text-status-error-solid">{error}</p>
          <Button onClick={refresh} variant="outline" className="mt-4">
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
        <Button onClick={refresh} variant="outline" size="sm" disabled={loading}>
          <RefreshCw className={cn('mr-2 h-4 w-4', loading && 'animate-spin')} />
          Atualizar
        </Button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <QualityMetricCard
          title="Avaliadas"
          value={metrics?.avaliadas ?? 0}
          icon={CheckCircle2}
          color="green"
        />
        <QualityMetricCard
          title="Pendentes"
          value={metrics?.pendentes ?? 0}
          icon={ClipboardList}
          color="yellow"
        />
        <QualityMetricCard
          title="Score Medio"
          value={metrics?.scoreMedio ?? 0}
          suffix="/5"
          icon={Star}
          color="blue"
        />
        <QualityMetricCard
          title="Validacoes"
          value={metrics?.validacaoTaxa ?? 0}
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
              <p className="text-2xl font-bold">{metrics?.pendentes ?? 0} novas</p>
            </div>
            <div className="flex items-center gap-3">
              <MessageSquare className="h-8 w-8 text-status-info-solid" />
              <Button
                size="sm"
                onClick={() => setActiveTab('conversas')}
                disabled={(metrics?.pendentes ?? 0) === 0}
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
              <Lightbulb className="h-8 w-8 text-status-warning-solid" />
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
              {metrics.validacaoFalhas} falhas hoje (
              {calculateFailureRate(metrics.validacaoTaxa).toFixed(1)}%)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {metrics.padroesViolados.slice(0, MAX_PATTERNS_DISPLAYED).map((p) => (
                <div
                  key={p.padrao}
                  className="flex items-center gap-1 rounded-full bg-status-error px-3 py-1 text-sm"
                >
                  <AlertTriangle className="h-3 w-3 text-status-error-foreground" />
                  <span className="text-status-error-foreground">
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
