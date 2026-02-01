/**
 * Custom hooks para o módulo de Integridade
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Anomaly, IntegridadeData, IntegridadeKpis, AnomaliasSummary } from './types'
import { DEFAULT_KPIS, DEFAULT_ANOMALIAS_SUMMARY, ANOMALIAS_FETCH_LIMIT } from './constants'

/**
 * Parse da resposta de KPIs do backend
 * Backend retorna estrutura aninhada que precisa ser normalizada
 */
export function parseKpisResponse(kpisData: Record<string, unknown>): IntegridadeKpis {
  // Backend structure: { kpis: { health_score: { score, component_scores }, conversion_rate: { value }, time_to_fill: { time_to_fill_full: { avg_hours } } } }
  const kpisNested = (kpisData.kpis as Record<string, unknown>) || kpisData

  const healthScore =
    (kpisNested.health_score as Record<string, unknown>)?.score ?? kpisData.health_score ?? 0

  const conversionRate =
    (kpisNested.conversion_rate as Record<string, unknown>)?.value ?? kpisData.conversion_rate ?? 0

  const timeToFillNested = kpisNested.time_to_fill as Record<string, unknown>
  const timeToFillFull = timeToFillNested?.time_to_fill_full as Record<string, unknown>
  const timeToFill = (timeToFillFull?.avg_hours as number) ?? (kpisData.time_to_fill as number) ?? 0

  const healthScoreObj = kpisNested.health_score as Record<string, unknown>
  const componentScoresRaw = healthScoreObj?.component_scores as Record<string, unknown>

  return {
    healthScore: Number(healthScore),
    conversionRate: Number(conversionRate),
    timeToFill: Number(timeToFill),
    componentScores: {
      pressao: Number(componentScoresRaw?.pressao ?? 0),
      friccao: Number(componentScoresRaw?.friccao ?? 0),
      qualidade: Number(componentScoresRaw?.qualidade ?? 0),
      spam: Number(componentScoresRaw?.spam ?? 0),
    },
    recommendations: (healthScoreObj?.recommendations as string[]) || [],
  }
}

/**
 * Parse da resposta de anomalias do backend
 * Backend usa nomes diferentes (anomalies vs anomalias, snake_case vs camelCase)
 */
export function parseAnomaliasResponse(anomaliasData: Record<string, unknown>): {
  anomaliasList: Anomaly[]
  anomalias: AnomaliasSummary
} {
  // Backend uses "anomalies" key
  const rawAnomalies =
    (anomaliasData.anomalies as Record<string, unknown>[]) ||
    (anomaliasData.anomalias as Record<string, unknown>[]) ||
    []

  const anomaliasList: Anomaly[] = rawAnomalies.map((a) => ({
    id: String(a.id),
    tipo: String(a.tipo || a.type || ''),
    entidade: String(a.entidade || a.entity || ''),
    entidadeId: String(a.entidade_id || a.entity_id || ''),
    severidade: (a.severidade || a.severity || 'low') as Anomaly['severidade'],
    mensagem: String(a.mensagem || a.message || ''),
    criadaEm: String(a.criada_em || a.created_at || ''),
    resolvida: Boolean(a.resolvida || a.resolved || false),
  }))

  // Use summary from backend if available
  const summary = anomaliasData.summary as Record<string, unknown>
  const bySeverity = summary?.by_severity as Record<string, number>

  const abertas =
    bySeverity?.warning !== undefined && bySeverity?.critical !== undefined
      ? bySeverity.warning + bySeverity.critical
      : anomaliasList.filter((a) => !a.resolvida).length

  return {
    anomaliasList,
    anomalias: {
      abertas,
      resolvidas: anomaliasList.filter((a) => a.resolvida).length,
      total: (summary?.total as number) || anomaliasList.length,
    },
  }
}

interface UseIntegridadeDataReturn {
  data: IntegridadeData | null
  loading: boolean
  error: string | null
  fetchData: () => Promise<void>
  runAudit: () => Promise<void>
  resolveAnomaly: (anomalyId: string, notas: string) => Promise<void>
  runningAudit: boolean
}

/**
 * Hook para gerenciar dados de integridade
 * Encapsula fetching, parsing e ações (audit, resolve)
 */
export function useIntegridadeData(): UseIntegridadeDataReturn {
  const [data, setData] = useState<IntegridadeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runningAudit, setRunningAudit] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setError(null)

      const [kpisRes, anomaliasRes] = await Promise.all([
        fetch('/api/integridade/kpis').catch(() => null),
        fetch(`/api/integridade/anomalias?limit=${ANOMALIAS_FETCH_LIMIT}`).catch(() => null),
      ])

      // Parse KPIs
      let kpis = DEFAULT_KPIS
      if (kpisRes?.ok) {
        const kpisData = (await kpisRes.json()) as Record<string, unknown>
        kpis = parseKpisResponse(kpisData)
      }

      // Parse anomalias
      let anomaliasList: Anomaly[] = []
      let anomalias = DEFAULT_ANOMALIAS_SUMMARY
      if (anomaliasRes?.ok) {
        const anomaliasData = (await anomaliasRes.json()) as Record<string, unknown>
        const parsed = parseAnomaliasResponse(anomaliasData)
        anomaliasList = parsed.anomaliasList
        anomalias = parsed.anomalias
      }

      setData({
        kpis,
        anomalias,
        violacoes: anomalias.abertas,
        ultimaAuditoria: new Date().toISOString(),
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

  const runAudit = useCallback(async () => {
    setRunningAudit(true)
    try {
      const res = await fetch('/api/integridade/reconciliacao', { method: 'POST' })
      if (!res.ok) {
        const errorData = (await res.json().catch(() => ({}))) as Record<string, unknown>
        throw new Error((errorData.error as string) || 'Erro ao executar auditoria')
      }
      await fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao executar auditoria')
    } finally {
      setRunningAudit(false)
    }
  }, [fetchData])

  const resolveAnomaly = useCallback(
    async (anomalyId: string, notas: string) => {
      try {
        const res = await fetch(`/api/integridade/anomalias/${anomalyId}/resolver`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ notas, usuario: 'dashboard' }),
        })
        if (!res.ok) {
          const errorData = (await res.json().catch(() => ({}))) as Record<string, unknown>
          throw new Error((errorData.error as string) || 'Erro ao resolver anomalia')
        }
        await fetchData()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao resolver anomalia')
        throw err
      }
    },
    [fetchData]
  )

  return {
    data,
    loading,
    error,
    fetchData,
    runAudit,
    resolveAnomaly,
    runningAudit,
  }
}
