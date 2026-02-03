/**
 * Hook useMarketIntelligence - Sprint 46
 *
 * Gerencia estado e busca de dados de Market Intelligence.
 */

'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import type {
  AnalyticsPeriod,
  MarketOverviewResponse,
  VolumeResponse,
  PipelineResponse,
  GrupoRanking,
} from '@/types/market-intelligence'

// =============================================================================
// TYPES
// =============================================================================

export interface UseMarketIntelligenceOptions {
  period?: AnalyticsPeriod
  startDate?: string
  endDate?: string
  autoFetch?: boolean
}

export interface UseMarketIntelligenceReturn {
  // Dados
  overview: MarketOverviewResponse | null
  volume: VolumeResponse | null
  pipeline: PipelineResponse | null
  groupsRanking: GrupoRanking[] | null

  // Estado
  isLoading: boolean
  isRefreshing: boolean
  error: Error | null

  // Acoes
  refresh: () => Promise<void>
  setPeriod: (period: AnalyticsPeriod) => void
  setCustomPeriod: (startDate: string, endDate: string) => void

  // Metadata
  lastUpdated: Date | null
  period: AnalyticsPeriod
  customDates: { startDate: string; endDate: string } | null
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

async function fetchOverview(
  period: AnalyticsPeriod,
  startDate?: string,
  endDate?: string
): Promise<MarketOverviewResponse> {
  const params = new URLSearchParams({ period })
  if (period === 'custom' && startDate && endDate) {
    params.set('startDate', startDate)
    params.set('endDate', endDate)
  }

  const response = await fetch(`/api/market-intelligence/overview?${params}`)
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Erro ao buscar overview')
  }
  return response.json()
}

async function fetchVolume(
  period: AnalyticsPeriod,
  startDate?: string,
  endDate?: string
): Promise<VolumeResponse> {
  const params = new URLSearchParams({ period })
  if (period === 'custom' && startDate && endDate) {
    params.set('startDate', startDate)
    params.set('endDate', endDate)
  }

  const response = await fetch(`/api/market-intelligence/volume?${params}`)
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Erro ao buscar volume')
  }
  return response.json()
}

async function fetchPipeline(
  period: AnalyticsPeriod,
  startDate?: string,
  endDate?: string
): Promise<PipelineResponse> {
  const params = new URLSearchParams({ period })
  if (period === 'custom' && startDate && endDate) {
    params.set('startDate', startDate)
    params.set('endDate', endDate)
  }

  const response = await fetch(`/api/market-intelligence/pipeline?${params}`)
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Erro ao buscar pipeline')
  }
  return response.json()
}

async function fetchGroupsRanking(limit: number = 10): Promise<GrupoRanking[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    sortBy: 'vagas',
    order: 'desc',
    apenasAtivos: 'true',
  })

  const response = await fetch(`/api/market-intelligence/groups-ranking?${params}`)
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Erro ao buscar ranking de grupos')
  }
  const data = await response.json()
  return data.grupos || []
}

// =============================================================================
// HOOK
// =============================================================================

export function useMarketIntelligence(
  options: UseMarketIntelligenceOptions = {}
): UseMarketIntelligenceReturn {
  const { period: initialPeriod = '24h', startDate, endDate, autoFetch = true } = options

  // Estado
  const [period, setPeriodState] = useState<AnalyticsPeriod>(initialPeriod)
  const [customDates, setCustomDates] = useState<{
    startDate: string
    endDate: string
  } | null>(startDate && endDate ? { startDate, endDate } : null)
  const [overview, setOverview] = useState<MarketOverviewResponse | null>(null)
  const [volume, setVolume] = useState<VolumeResponse | null>(null)
  const [pipeline, setPipeline] = useState<PipelineResponse | null>(null)
  const [groupsRanking, setGroupsRanking] = useState<GrupoRanking[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  // Funcao de busca principal
  const fetchData = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) {
        setIsRefreshing(true)
      } else {
        setIsLoading(true)
      }
      setError(null)

      try {
        const currentStartDate = period === 'custom' ? customDates?.startDate : undefined
        const currentEndDate = period === 'custom' ? customDates?.endDate : undefined

        // Buscar todos os dados em paralelo
        const [overviewData, volumeData, pipelineData, groupsData] = await Promise.all([
          fetchOverview(period, currentStartDate, currentEndDate),
          fetchVolume(period, currentStartDate, currentEndDate),
          fetchPipeline(period, currentStartDate, currentEndDate),
          fetchGroupsRanking(10),
        ])

        setOverview(overviewData)
        setVolume(volumeData)
        setPipeline(pipelineData)
        setGroupsRanking(groupsData)
        setLastUpdated(new Date())
      } catch (err) {
        const errorMessage = err instanceof Error ? err : new Error('Erro desconhecido')
        setError(errorMessage)
        console.error('[useMarketIntelligence] Erro:', err)
      } finally {
        setIsLoading(false)
        setIsRefreshing(false)
      }
    },
    [period, customDates]
  )

  // Funcao de refresh exposta
  const refresh = useCallback(async () => {
    await fetchData(true)
  }, [fetchData])

  // Funcao para mudar periodo
  const setPeriod = useCallback((newPeriod: AnalyticsPeriod) => {
    if (newPeriod !== 'custom') {
      setCustomDates(null)
    }
    setPeriodState(newPeriod)
  }, [])

  // Funcao para definir periodo customizado
  const setCustomPeriod = useCallback((newStartDate: string, newEndDate: string) => {
    setCustomDates({ startDate: newStartDate, endDate: newEndDate })
    setPeriodState('custom')
  }, [])

  // Effect para buscar dados iniciais e quando periodo muda
  useEffect(() => {
    if (autoFetch) {
      fetchData()
    }
  }, [fetchData, autoFetch])

  // Memoizar retorno para evitar re-renders desnecessarios
  const returnValue = useMemo(
    (): UseMarketIntelligenceReturn => ({
      overview,
      volume,
      pipeline,
      groupsRanking,
      isLoading,
      isRefreshing,
      error,
      refresh,
      setPeriod,
      setCustomPeriod,
      lastUpdated,
      period,
      customDates,
    }),
    [
      overview,
      volume,
      pipeline,
      groupsRanking,
      isLoading,
      isRefreshing,
      error,
      refresh,
      setPeriod,
      setCustomPeriod,
      lastUpdated,
      period,
      customDates,
    ]
  )

  return returnValue
}

export default useMarketIntelligence
