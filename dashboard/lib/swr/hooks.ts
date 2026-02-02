import useSWR from 'swr'
import useSWRMutation from 'swr/mutation'
import { realtimeConfig, staticConfig, postFetcher } from './config'

/**
 * Hooks SWR para Data Fetching.
 *
 * Sprint 44 T05.3: Implementar SWR para Data Fetching.
 */

// Types
interface MetricsData {
  conversasAtivas: number
  taxaResposta: number
  taxaConversao: number
  tempoMedioResposta: number
  tendencias: {
    conversas: number
    resposta: number
    conversao: number
    tempo: number
  }
}

interface FunnelData {
  etapas: Array<{
    nome: string
    total: number
    percentual: number
  }>
  periodo: string
}

interface ChipData {
  id: string
  telefone: string
  status: string
  trust_score: number
  msgs_enviadas_hoje: number
  instancia: string
}

interface AlertData {
  id: string
  tipo: string
  severidade: 'info' | 'warning' | 'error' | 'critical'
  mensagem: string
  created_at: string
  resolvido: boolean
}

interface ConversaData {
  id: string
  cliente_id: string
  status: string
  controlled_by: string
  created_at: string
  updated_at: string
  cliente?: {
    telefone: string
    primeiro_nome: string
  }
}

/**
 * Hook para métricas do dashboard.
 */
export function useMetrics(period: string = '7d') {
  const { data, error, isLoading, mutate } = useSWR<MetricsData>(
    `/api/dashboard/metrics?period=${period}`,
    {
      ...realtimeConfig,
      refreshInterval: 60000, // 1 minuto
    }
  )

  return {
    metrics: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para funil de conversão.
 */
export function useFunnel(period: string = '7d') {
  const { data, error, isLoading, mutate } = useSWR<FunnelData>(
    `/api/dashboard/funnel?period=${period}`,
    realtimeConfig
  )

  return {
    funnel: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para lista de chips.
 */
export function useChips(filters?: { status?: string; instancia?: string }) {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.instancia) params.set('instancia', filters.instancia)

  const queryString = params.toString()
  const url = queryString ? `/api/chips?${queryString}` : '/api/chips'

  const { data, error, isLoading, mutate } = useSWR<ChipData[]>(url, realtimeConfig)

  return {
    chips: data ?? [],
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para detalhes de um chip.
 */
export function useChip(chipId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ChipData>(
    chipId ? `/api/chips/${chipId}` : null,
    staticConfig
  )

  return {
    chip: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para alertas.
 */
export function useAlerts(limit: number = 10) {
  const { data, error, isLoading, mutate } = useSWR<AlertData[]>(
    `/api/alerts?limit=${limit}`,
    realtimeConfig
  )

  return {
    alerts: data ?? [],
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para conversas.
 */
export function useConversas(filters?: { status?: string; controlled_by?: string }) {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.controlled_by) params.set('controlled_by', filters.controlled_by)

  const queryString = params.toString()
  const url = queryString ? `/api/conversas?${queryString}` : '/api/conversas'

  const { data, error, isLoading, mutate } = useSWR<ConversaData[]>(url, realtimeConfig)

  return {
    conversas: data ?? [],
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para detalhes de uma conversa.
 */
export function useConversa(conversaId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ConversaData>(
    conversaId ? `/api/conversas/${conversaId}` : null,
    staticConfig
  )

  return {
    conversa: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  }
}

/**
 * Hook para ações em chips (mutation).
 */
export function useChipAction() {
  const { trigger, isMutating, error } = useSWRMutation(
    '/api/chips/action',
    async (url: string, { arg }: { arg: { chipId: string; action: string; reason?: string } }) => {
      return postFetcher(url, arg)
    }
  )

  return {
    executeAction: trigger,
    isLoading: isMutating,
    error,
  }
}

/**
 * Hook para resolver alertas (mutation).
 */
export function useResolveAlert() {
  const { trigger, isMutating, error } = useSWRMutation(
    '/api/alerts/resolve',
    async (url: string, { arg }: { arg: { alertId: string } }) => {
      return postFetcher(url, arg)
    }
  )

  return {
    resolveAlert: trigger,
    isLoading: isMutating,
    error,
  }
}
