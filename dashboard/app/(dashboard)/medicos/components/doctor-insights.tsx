'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ThumbsUp,
  ThumbsDown,
  Clock,
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Heart,
  Ban,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  fetchClienteInsights,
  ClienteInsightsResponse,
  ClienteInsight,
  interesseLabels,
  proximoPassoLabels,
  objecaoLabels,
} from '@/lib/api/extraction'

interface DoctorInsightsProps {
  doctorId: string
}

export function DoctorInsights({ doctorId }: DoctorInsightsProps) {
  const [data, setData] = useState<ClienteInsightsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const carregarInsights = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchClienteInsights(doctorId, 20)
      setData(result)
    } catch (err) {
      console.error('Erro ao carregar insights:', err)
      setError('Erro ao carregar insights')
    } finally {
      setLoading(false)
    }
  }, [doctorId])

  useEffect(() => {
    carregarInsights()
  }, [carregarInsights])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-status-error-solid" />
          <p className="text-status-error-foreground">{error}</p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.total === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Sparkles className="mx-auto mb-4 h-12 w-12 text-gray-300" />
          <p className="text-muted-foreground">
            Nenhum insight disponivel para este medico.
          </p>
          <p className="mt-1 text-sm text-gray-400">
            Insights sao gerados automaticamente a partir das conversas.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Perfil de Interesse */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Perfil de Interesse
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Score Medio de Interesse</span>
              <span className="text-muted-foreground">
                {(data.resumo.interesse_score_medio * 10).toFixed(1)}/10
              </span>
            </div>
            <Progress value={data.resumo.interesse_score_medio * 100} className="h-3" />
          </div>

          <div className="grid grid-cols-3 gap-4 border-t pt-4 text-center">
            <div>
              <p className="text-xl font-bold text-status-success-solid">
                {data.resumo.interesse_positivo}
              </p>
              <p className="text-xs text-muted-foreground">Positivos</p>
            </div>
            <div>
              <p className="text-xl font-bold text-status-error-solid">
                {data.resumo.interesse_negativo}
              </p>
              <p className="text-xs text-muted-foreground">Negativos</p>
            </div>
            <div>
              <p className="text-xl font-bold">{data.total}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Preferências e Restrições Detectadas */}
      {(data.insights.some((i) => i.preferencias?.length > 0) ||
        data.insights.some((i) => i.restricoes?.length > 0)) && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Preferências */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Heart className="h-4 w-4 text-status-success-solid" />
                Preferencias Detectadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {getUniquePreferences(data.insights).map((pref, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {pref}
                  </Badge>
                ))}
                {getUniquePreferences(data.insights).length === 0 && (
                  <p className="text-sm text-muted-foreground">Nenhuma detectada</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Restrições */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Ban className="h-4 w-4 text-status-error-solid" />
                Restricoes Conhecidas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {getUniqueRestrictions(data.insights).map((rest, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {rest}
                  </Badge>
                ))}
                {getUniqueRestrictions(data.insights).length === 0 && (
                  <p className="text-sm text-muted-foreground">Nenhuma detectada</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Histórico de Interações */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Historico de Interacoes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {data.insights.map((insight) => (
              <InsightItem key={insight.id} insight={insight} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

interface InsightItemProps {
  insight: ClienteInsight
}

function InsightItem({ insight }: InsightItemProps) {
  const InteresseIcon =
    insight.interesse === 'positivo'
      ? ThumbsUp
      : insight.interesse === 'negativo'
        ? ThumbsDown
        : AlertTriangle

  const interesseColor =
    insight.interesse === 'positivo'
      ? 'text-status-success-solid'
      : insight.interesse === 'negativo'
        ? 'text-status-error-solid'
        : 'text-muted-foreground'

  return (
    <div className="flex items-start gap-3 border-b pb-4 last:border-0 last:pb-0">
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full ${
          insight.interesse === 'positivo'
            ? 'bg-status-success/10'
            : insight.interesse === 'negativo'
              ? 'bg-status-error/10'
              : 'bg-muted'
        }`}
      >
        <InteresseIcon className={`h-4 w-4 ${interesseColor}`} />
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-medium">
              {interesseLabels[insight.interesse] || insight.interesse}
            </span>
            <span className="text-sm text-muted-foreground">
              ({(insight.interesse_score * 10).toFixed(1)})
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(insight.created_at), {
              addSuffix: true,
              locale: ptBR,
            })}
          </span>
        </div>

        {insight.disponibilidade_mencionada && (
          <p className="text-sm text-muted-foreground">
            Disponibilidade: {insight.disponibilidade_mencionada}
          </p>
        )}

        {insight.objecao_tipo && (
          <Badge variant="outline" className="text-xs">
            Objecao: {objecaoLabels[insight.objecao_tipo] || insight.objecao_tipo}
          </Badge>
        )}

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="secondary" className="text-xs">
            {proximoPassoLabels[insight.proximo_passo] || insight.proximo_passo}
          </Badge>
          <span>Confianca: {(insight.confianca * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  )
}

// Helpers
function getUniquePreferences(insights: ClienteInsight[]): string[] {
  const all = insights.flatMap((i) => i.preferencias || [])
  const unique = Array.from(new Set(all.map((p) => p.toLowerCase())))
  return unique.slice(0, 8)
}

function getUniqueRestrictions(insights: ClienteInsight[]): string[] {
  const all = insights.flatMap((i) => i.restricoes || [])
  const unique = Array.from(new Set(all.map((r) => r.toLowerCase())))
  return unique.slice(0, 8)
}
