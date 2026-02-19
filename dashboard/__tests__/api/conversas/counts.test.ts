/**
 * Tests for GET /api/conversas/counts
 * Sprint 64: Real counts (no more 30% guessing)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/conversas/counts/route'
import { NextRequest } from 'next/server'

// ---------- Supabase mock ----------

interface MockQueryResult {
  data: unknown[] | unknown | null
  error: unknown
  count?: number | null
}

let rpcResult: MockQueryResult = { data: null, error: { message: 'not available' } }
let chipFilterResult: MockQueryResult = { data: [], error: null }
let activeConversationsResult: MockQueryResult = { data: [], error: null }
let interacoesResult: MockQueryResult = { data: [], error: null }
let handoffsResult: MockQueryResult = { data: [], error: null }
let encerradasResult: MockQueryResult = { data: null, error: null, count: 0 }

function makeThenableChain(resultGetter: () => MockQueryResult) {
  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (prop === 'then') {
        return (
          onFulfilled?: (val: MockQueryResult) => unknown,
          onRejected?: (reason: unknown) => unknown
        ) => {
          return Promise.resolve(resultGetter()).then(onFulfilled, onRejected)
        }
      }
      if (typeof prop === 'string') {
        return vi.fn((..._args: unknown[]) => proxy)
      }
      return undefined
    },
  }
  const proxy = new Proxy({}, handler)
  return proxy
}

let fromCallIndex = 0

const mockFrom = vi.fn((table: string) => {
  if (table === 'conversation_chips') {
    return makeThenableChain(() => chipFilterResult)
  }
  if (table === 'conversations') {
    fromCallIndex++
    if (fromCallIndex === 1) {
      return makeThenableChain(() => activeConversationsResult)
    }
    return makeThenableChain(() => encerradasResult)
  }
  if (table === 'interacoes') {
    return makeThenableChain(() => interacoesResult)
  }
  if (table === 'handoffs') {
    return makeThenableChain(() => handoffsResult)
  }
  return makeThenableChain(() => ({ data: [], error: null }))
})

const mockRpc = vi.fn((fn: string) => {
  if (fn === 'get_last_messages') {
    return makeThenableChain(() => interacoesResult)
  }
  // get_supervision_tab_counts returns directly (not thenable)
  return rpcResult
})

const mockSupabase = { from: mockFrom, rpc: mockRpc }

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

// ---------- Helpers ----------

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/conversas/counts?${searchParams}`
  return new NextRequest(url)
}

function resetState() {
  rpcResult = { data: null, error: { message: 'not available' } }
  chipFilterResult = { data: [], error: null }
  activeConversationsResult = { data: [], error: null }
  interacoesResult = { data: [], error: null }
  handoffsResult = { data: [], error: null }
  encerradasResult = { data: null, error: null, count: 0 }
  fromCallIndex = 0
}

// ---------- Tests ----------

describe('GET /api/conversas/counts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetState()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses RPC when available', async () => {
    const expectedCounts = {
      atencao: 3,
      julia_ativa: 10,
      aguardando: 5,
      encerradas: 2,
    }
    rpcResult = { data: expectedCounts, error: null }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(mockRpc).toHaveBeenCalledWith('get_supervision_tab_counts', expect.any(Object))
    expect(data).toEqual(expectedCounts)
  })

  it('returns empty counts when chip_id has no conversations', async () => {
    chipFilterResult = { data: [], error: null }

    const request = createRequest({ chip_id: 'chip-empty' })
    const response = await GET(request)
    const data = await response.json()

    expect(data).toEqual({
      atencao: 0,
      julia_ativa: 0,
      aguardando: 0,
      encerradas: 0,
    })
  })

  it('falls back to manual computation when RPC fails', async () => {
    rpcResult = { data: null, error: { message: 'function not found' } }

    // Active conversations: 1 human, 1 AI
    activeConversationsResult = {
      data: [
        {
          id: 'conv-1',
          status: 'active',
          controlled_by: 'human',
          last_message_at: new Date().toISOString(),
        },
        {
          id: 'conv-2',
          status: 'active',
          controlled_by: 'ai',
          last_message_at: new Date().toISOString(),
        },
      ],
      error: null,
    }

    // Last messages: conv-2 last msg is outgoing (julia)
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-2',
          autor_tipo: 'julia',
          created_at: new Date().toISOString(),
        },
      ],
      error: null,
    }

    handoffsResult = { data: [], error: null }
    encerradasResult = { data: null, error: null, count: 1 }

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    // conv-1 is human-controlled -> atencao
    expect(data.atencao).toBe(1)
    // conv-2 is AI, last msg outgoing -> aguardando
    expect(data.aguardando).toBe(1)
    expect(data.encerradas).toBe(1)

    consoleSpy.mockRestore()
  })

  it('returns zero counts on error', async () => {
    rpcResult = { data: null, error: { message: 'rpc fail' } }
    // Make fallback also throw
    mockFrom.mockImplementation(() => {
      throw new Error('DB error')
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const consoleSpy2 = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data).toEqual({
      atencao: 0,
      julia_ativa: 0,
      aguardando: 0,
      encerradas: 0,
    })

    consoleSpy.mockRestore()
    consoleSpy2.mockRestore()
  })
})
