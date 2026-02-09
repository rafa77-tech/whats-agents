/**
 * SWR Hooks para o modulo Conversas
 * Sprint 54: Supervision Dashboard
 */

import useSWR from 'swr'
import { realtimeConfig, staticConfig } from '@/lib/swr/config'
import type {
  ConversationListResponse,
  ConversationDetail,
  TabCounts,
  SupervisionTab,
  DoctorContextData,
} from '@/types/conversas'

// ============================================
// Conversation List Hook
// ============================================

interface UseConversationListParams {
  tab?: SupervisionTab | undefined
  search?: string | undefined
  chipId?: string | null | undefined
  page?: number | undefined
  perPage?: number | undefined
}

interface UseConversationListReturn {
  conversations: ConversationListResponse | undefined
  isLoading: boolean
  isError: boolean
  error: Error | undefined
  refresh: () => void
  mutate: () => Promise<ConversationListResponse | undefined>
}

export function useConversationList(
  params: UseConversationListParams = {}
): UseConversationListReturn {
  const { tab, search, chipId, page = 1, perPage = 50 } = params

  const urlParams = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  })

  if (tab) urlParams.set('tab', tab)
  if (search) urlParams.set('search', search)
  if (chipId) urlParams.set('chip_id', chipId)

  const url = `/api/conversas?${urlParams.toString()}`

  const { data, error, isLoading, mutate } = useSWR<ConversationListResponse>(url, {
    ...realtimeConfig,
    refreshInterval: 15000, // 15s for conversation list
  })

  return {
    conversations: data,
    isLoading,
    isError: !!error,
    error: error as Error | undefined,
    refresh: () => {
      void mutate()
    },
    mutate: () => mutate(),
  }
}

// ============================================
// Tab Counts Hook
// ============================================

interface UseTabCountsReturn {
  counts: TabCounts
  isLoading: boolean
  isError: boolean
  refresh: () => void
}

export function useTabCounts(chipId?: string | null): UseTabCountsReturn {
  const url = chipId ? `/api/conversas/counts?chip_id=${chipId}` : '/api/conversas/counts'

  const { data, error, isLoading, mutate } = useSWR<TabCounts>(url, {
    ...realtimeConfig,
    refreshInterval: 30000, // 30s for counts
  })

  const defaultCounts: TabCounts = {
    atencao: 0,
    julia_ativa: 0,
    aguardando: 0,
    encerradas: 0,
  }

  return {
    counts: data ?? defaultCounts,
    isLoading,
    isError: !!error,
    refresh: () => {
      void mutate()
    },
  }
}

// ============================================
// Conversation Detail Hook
// ============================================

interface UseConversationDetailReturn {
  conversation: ConversationDetail | undefined
  isLoading: boolean
  isError: boolean
  error: Error | undefined
  refresh: () => void
}

export function useConversationDetail(conversationId: string | null): UseConversationDetailReturn {
  const { data, error, isLoading, mutate } = useSWR<ConversationDetail>(
    conversationId ? `/api/conversas/${conversationId}` : null,
    {
      ...realtimeConfig,
      refreshInterval: 10000, // 10s for active conversation
    }
  )

  return {
    conversation: data,
    isLoading,
    isError: !!error,
    error: error as Error | undefined,
    refresh: () => {
      void mutate()
    },
  }
}

// ============================================
// Doctor Context Hook (Phase 2)
// ============================================

interface UseDoctorContextReturn {
  context: DoctorContextData | undefined
  isLoading: boolean
  isError: boolean
  refresh: () => void
}

export function useDoctorContext(conversationId: string | null): UseDoctorContextReturn {
  const { data, error, isLoading, mutate } = useSWR<DoctorContextData>(
    conversationId ? `/api/conversas/${conversationId}/context` : null,
    {
      ...staticConfig,
      revalidateOnFocus: true, // Refresh when user tabs back
    }
  )

  return {
    context: data,
    isLoading,
    isError: !!error,
    refresh: () => {
      void mutate()
    },
  }
}
