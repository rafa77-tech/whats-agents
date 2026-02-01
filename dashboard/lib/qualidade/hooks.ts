/**
 * Custom hooks para o modulo de Qualidade
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import type {
  QualityMetrics,
  Conversation,
  ConversationDetail,
  Suggestion,
  ConversationRatings,
  SuggestionStatus,
  CreateSuggestionPayload,
  UseQualidadeMetricsReturn,
  UseConversationsReturn,
  UseSuggestionsReturn,
  UseConversationDetailReturn,
  PerformanceMetricsResponse,
  ValidationMetricsResponse,
  ConversationsResponse,
  ConversationDetailResponse,
  SuggestionsResponse,
} from './types'
import {
  parseMetricsResponse,
  parseConversationsResponse,
  parseConversationDetailResponse,
  parseSuggestionsResponse,
  buildConversationsUrl,
  buildSuggestionsUrl,
} from './formatters'
import { API_ENDPOINTS, CONVERSATIONS_FETCH_LIMIT } from './constants'

// =============================================================================
// Hook: useQualidadeMetrics
// =============================================================================

/**
 * Hook para buscar metricas de qualidade
 */
export function useQualidadeMetrics(): UseQualidadeMetricsReturn {
  const [metrics, setMetrics] = useState<QualityMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)

      const [performanceRes, validacaoRes] = await Promise.all([
        fetch(API_ENDPOINTS.metricsPerformance).catch(() => null),
        fetch(API_ENDPOINTS.metricsValidation).catch(() => null),
      ])

      let performanceData: PerformanceMetricsResponse | null = null
      if (performanceRes?.ok) {
        performanceData = (await performanceRes.json()) as PerformanceMetricsResponse
      }

      let validacaoData: ValidationMetricsResponse | null = null
      if (validacaoRes?.ok) {
        validacaoData = (await validacaoRes.json()) as ValidationMetricsResponse
      }

      setMetrics(parseMetricsResponse(performanceData, validacaoData))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar metricas')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { metrics, loading, error, refresh }
}

// =============================================================================
// Hook: useConversations
// =============================================================================

/**
 * Hook para buscar lista de conversas com filtro
 */
export function useConversations(filter: string = 'false'): UseConversationsReturn {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)
      const url = buildConversationsUrl(
        API_ENDPOINTS.conversations,
        filter,
        CONVERSATIONS_FETCH_LIMIT
      )

      const res = await fetch(url)
      if (res.ok) {
        const data = (await res.json()) as ConversationsResponse
        setConversations(parseConversationsResponse(data))
      } else {
        throw new Error('Erro ao carregar conversas')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar conversas')
      setConversations([])
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { conversations, loading, error, refresh }
}

// =============================================================================
// Hook: useConversationDetail
// =============================================================================

/**
 * Hook para buscar detalhes de uma conversa e salvar avaliacao
 */
export function useConversationDetail(conversationId: string): UseConversationDetailReturn {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchConversation = async () => {
      try {
        setError(null)
        const res = await fetch(API_ENDPOINTS.conversationDetail(conversationId))
        if (res.ok) {
          const data = (await res.json()) as ConversationDetailResponse
          setConversation(parseConversationDetailResponse(data))
        } else {
          throw new Error('Erro ao carregar conversa')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao carregar conversa')
      } finally {
        setLoading(false)
      }
    }

    fetchConversation()
  }, [conversationId])

  const saveEvaluation = useCallback(
    async (ratings: ConversationRatings, observacoes: string) => {
      setSaving(true)
      try {
        const res = await fetch(API_ENDPOINTS.evaluations, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversa_id: conversationId,
            naturalidade: ratings.naturalidade,
            persona: ratings.persona,
            objetivo: ratings.objetivo,
            satisfacao: ratings.satisfacao,
            observacoes,
          }),
        })

        if (!res.ok) {
          const errorData = (await res.json().catch(() => ({}))) as Record<string, unknown>
          throw new Error((errorData.error as string) || 'Erro ao salvar avaliacao')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao salvar avaliacao')
        throw err
      } finally {
        setSaving(false)
      }
    },
    [conversationId]
  )

  return { conversation, loading, error, saveEvaluation, saving }
}

// =============================================================================
// Hook: useSuggestions
// =============================================================================

/**
 * Hook para buscar sugestoes com filtro e acoes
 */
export function useSuggestions(statusFilter: string = 'pending'): UseSuggestionsReturn {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)
      const url = buildSuggestionsUrl(API_ENDPOINTS.suggestions, statusFilter)

      const res = await fetch(url)
      if (res.ok) {
        const data = (await res.json()) as SuggestionsResponse
        setSuggestions(parseSuggestionsResponse(data))
      } else {
        throw new Error('Erro ao carregar sugestoes')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar sugestoes')
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    refresh()
  }, [refresh])

  const updateStatus = useCallback(
    async (id: string, status: SuggestionStatus) => {
      setActionLoading(id)
      try {
        const res = await fetch(API_ENDPOINTS.suggestionDetail(id), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status }),
        })

        if (!res.ok) {
          const errorData = (await res.json().catch(() => ({}))) as Record<string, unknown>
          throw new Error((errorData.error as string) || 'Erro ao atualizar status')
        }

        await refresh()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao atualizar status')
        throw err
      } finally {
        setActionLoading(null)
      }
    },
    [refresh]
  )

  const create = useCallback(
    async (payload: CreateSuggestionPayload) => {
      try {
        const res = await fetch(API_ENDPOINTS.suggestions, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tipo: payload.tipo,
            descricao: payload.descricao,
            exemplos: payload.exemplos || undefined,
          }),
        })

        if (!res.ok) {
          const errorData = (await res.json().catch(() => ({}))) as Record<string, unknown>
          throw new Error((errorData.error as string) || 'Erro ao criar sugestao')
        }

        await refresh()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao criar sugestao')
        throw err
      }
    },
    [refresh]
  )

  return { suggestions, loading, error, refresh, updateStatus, create, actionLoading }
}
