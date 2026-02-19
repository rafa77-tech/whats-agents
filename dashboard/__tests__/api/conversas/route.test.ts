/**
 * Testes para GET /api/conversas
 * Sprint 64: Updated for server-side tab filtering, attention_reason, unread_count
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/conversas/route'
import { NextRequest } from 'next/server'

// ---------- Supabase mock ----------

interface MockQueryResult {
  data: unknown[] | null
  error: unknown
  count?: number | null
}

let conversationsResult: MockQueryResult = { data: [], error: null }
let chipFilterResult: MockQueryResult = { data: [], error: null }
let chipEnrichResult: MockQueryResult = { data: [], error: null }
let interacoesResult: MockQueryResult = { data: [], error: null }
let handoffsResult: MockQueryResult = { data: [], error: null }

// Track calls
let conversationsOrCalls: string[] = []
let chipFilterEqCalls: { field: string; value: string }[] = []

// The route calls `from('conversation_chips')` potentially twice:
// 1) when chip_id param is set (filter query)
// 2) in the enrichment Promise.all
// We track via a flag: if chip_id is in the request, first call is filter.
let hasChipIdParam = false
let chipCallIndex = 0

/**
 * Creates a "thenable" chain object. Every method returns itself,
 * and it implements PromiseLike so it resolves when awaited.
 */
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
      // Any chained method returns the proxy itself
      if (typeof prop === 'string') {
        return vi.fn((..._args: unknown[]) => proxy)
      }
      return undefined
    },
  }
  const proxy = new Proxy({}, handler)
  return proxy
}

// The conversations chain needs special tracking for .or() and .in() calls
function makeConversationsChain() {
  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (prop === 'then') {
        return (
          onFulfilled?: (val: MockQueryResult) => unknown,
          onRejected?: (reason: unknown) => unknown
        ) => {
          return Promise.resolve(conversationsResult).then(onFulfilled, onRejected)
        }
      }
      if (prop === 'or') {
        return vi.fn((filter: string) => {
          conversationsOrCalls.push(filter)
          return proxy
        })
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

// chip filter chain: tracks eq calls
function makeChipFilterChain() {
  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (prop === 'then') {
        return (
          onFulfilled?: (val: MockQueryResult) => unknown,
          onRejected?: (reason: unknown) => unknown
        ) => {
          return Promise.resolve(chipFilterResult).then(onFulfilled, onRejected)
        }
      }
      if (prop === 'eq') {
        return vi.fn((field: string, value: string) => {
          chipFilterEqCalls.push({ field, value })
          return proxy
        })
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

const mockFrom = vi.fn((table: string) => {
  if (table === 'conversations') {
    return makeConversationsChain()
  }
  if (table === 'conversation_chips') {
    chipCallIndex++
    if (hasChipIdParam && chipCallIndex === 1) {
      return makeChipFilterChain()
    }
    return makeThenableChain(() => chipEnrichResult)
  }
  if (table === 'interacoes') {
    return makeThenableChain(() => interacoesResult)
  }
  if (table === 'handoffs') {
    return makeThenableChain(() => handoffsResult)
  }
  return makeThenableChain(() => ({ data: [], error: null }))
})

const mockSupabase = { from: mockFrom }

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

// ---------- Helpers ----------

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/conversas?${searchParams}`
  return new NextRequest(url)
}

function resetState() {
  conversationsResult = { data: [], error: null }
  chipFilterResult = { data: [], error: null }
  chipEnrichResult = { data: [], error: null }
  interacoesResult = { data: [], error: null }
  handoffsResult = { data: [], error: null }
  conversationsOrCalls = []
  chipFilterEqCalls = []
  hasChipIdParam = false
  chipCallIndex = 0
}

// Sample data
const sampleConversation = {
  id: 'conv-1',
  status: 'active',
  controlled_by: 'ai',
  message_count: 5,
  last_message_at: new Date().toISOString(),
  created_at: '2024-01-01T00:00:00Z',
  cliente_id: 'cli-1',
  clientes: {
    id: 'cli-1',
    primeiro_nome: 'Carlos',
    sobrenome: 'Silva',
    telefone: '5511999999999',
    stage_jornada: 'contato',
    especialidade: 'Cardiologia',
  },
}

// ---------- Tests ----------

describe('GET /api/conversas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetState()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns list of conversations with enrichment', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    chipEnrichResult = {
      data: [
        {
          conversa_id: 'conv-1',
          chips: {
            id: 'chip-1',
            telefone: '5511777777777',
            instance_name: 'julia-01',
            status: 'active',
            trust_level: 'high',
          },
        },
      ],
      error: null,
    }
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-1',
          conteudo: 'Oi doutor!',
          autor_tipo: 'julia',
          created_at: '2024-01-10T10:00:00Z',
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(1)
    expect(data.data[0].id).toBe('conv-1')
    expect(data.data[0].cliente_nome).toBe('Carlos Silva')
    expect(data.data[0].cliente_telefone).toBe('5511999999999')
    expect(data.data[0].chip).toEqual({
      id: 'chip-1',
      telefone: '5511777777777',
      instance_name: 'julia-01',
      status: 'active',
      trust_level: 'high',
    })
    expect(data.data[0].last_message).toBe('Oi doutor!')
    expect(data.data[0].last_message_direction).toBe('saida')
    expect(data.data[0].especialidade).toBe('Cardiologia')
    expect(data.total).toBe(1)
    expect(data.pages).toBe(1)
  })

  it('returns empty result when no conversations exist', async () => {
    conversationsResult = { data: [], error: null }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toEqual([])
    expect(data.total).toBe(0)
    expect(data.pages).toBe(0)
  })

  it('filters by tab=atencao (human controlled conversations)', async () => {
    const humanConv = { ...sampleConversation, id: 'conv-human', controlled_by: 'human' }
    const aiConv = { ...sampleConversation, id: 'conv-ai', controlled_by: 'ai' }
    conversationsResult = { data: [humanConv, aiConv], error: null }

    const request = createRequest({ tab: 'atencao' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    // Human-controlled should be categorized as atencao
    const atencaoConvs = data.data.filter(
      (c: { attention_reason: string | null }) => c.attention_reason !== null
    )
    expect(atencaoConvs.length).toBeGreaterThanOrEqual(1)
    expect(atencaoConvs[0].id).toBe('conv-human')
  })

  it('filters by tab=encerradas (completed conversations)', async () => {
    const completedConv = { ...sampleConversation, id: 'conv-done', status: 'completed' }
    conversationsResult = { data: [completedConv], error: null }

    const request = createRequest({ tab: 'encerradas' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(1)
    expect(data.data[0].id).toBe('conv-done')
  })

  it('filters by tab=aguardando (AI sent last message)', async () => {
    const conv = { ...sampleConversation, id: 'conv-waiting', controlled_by: 'ai' }
    conversationsResult = { data: [conv], error: null }
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-waiting',
          conteudo: 'Tem interesse?',
          autor_tipo: 'julia',
          created_at: '2024-01-10T10:00:00Z',
        },
      ],
      error: null,
    }

    const request = createRequest({ tab: 'aguardando' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(1)
    expect(data.data[0].id).toBe('conv-waiting')
    expect(data.data[0].last_message_direction).toBe('saida')
  })

  it('filters by chip_id', async () => {
    hasChipIdParam = true
    chipFilterResult = { data: [{ conversa_id: 'conv-1' }], error: null }
    conversationsResult = { data: [sampleConversation], error: null }

    const request = createRequest({ chip_id: 'chip-abc' })
    const response = await GET(request)
    await response.json()

    expect(response.status).toBe(200)
    expect(mockFrom).toHaveBeenCalledWith('conversation_chips')
    expect(chipFilterEqCalls).toEqual(
      expect.arrayContaining([expect.objectContaining({ field: 'chip_id', value: 'chip-abc' })])
    )
  })

  it('returns empty when chip_id matches no conversations', async () => {
    hasChipIdParam = true
    chipFilterResult = { data: [], error: null }

    const request = createRequest({ chip_id: 'chip-nonexistent' })
    const response = await GET(request)
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data).toEqual([])
    expect(body.total).toBe(0)
    expect(body.pages).toBe(0)
  })

  it('applies search filter via or() call', async () => {
    conversationsResult = { data: [sampleConversation], error: null }

    const request = createRequest({ search: 'Carlos' })
    const response = await GET(request)
    await response.json()

    expect(response.status).toBe(200)
    expect(conversationsOrCalls.length).toBeGreaterThan(0)
    expect(conversationsOrCalls[0]).toContain('Carlos')
  })

  it('paginates results correctly', async () => {
    const conversations = Array.from({ length: 5 }, (_, i) => ({
      ...sampleConversation,
      id: `conv-${i}`,
    }))
    conversationsResult = { data: conversations, error: null }

    const request = createRequest({ page: '2', per_page: '2' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(2)
    expect(data.data[0].id).toBe('conv-2')
    expect(data.data[1].id).toBe('conv-3')
    expect(data.total).toBe(5)
    expect(data.pages).toBe(3)
  })

  it('returns empty result gracefully on Supabase error', async () => {
    conversationsResult = { data: null, error: { message: 'Database error' } }

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toEqual([])
    expect(data.total).toBe(0)
    expect(data.pages).toBe(0)

    consoleSpy.mockRestore()
  })

  it('maps medico autor_tipo to entrada direction', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-1',
          conteudo: 'Tenho interesse sim',
          autor_tipo: 'medico',
          created_at: '2024-01-10T10:00:00Z',
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].last_message_direction).toBe('entrada')
  })

  it('includes handoff info when handoff exists', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    handoffsResult = {
      data: [
        {
          conversation_id: 'conv-1',
          motivo: 'Medico irritado',
          status: 'pendente',
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].has_handoff).toBe(true)
    expect(data.data[0].handoff_reason).toBe('Medico irritado')
  })

  it('handles conversation with null cliente fields gracefully', async () => {
    const convNullCliente = {
      ...sampleConversation,
      clientes: {
        id: 'cli-1',
        primeiro_nome: null,
        sobrenome: null,
        telefone: '5511999999999',
        stage_jornada: null,
        especialidade: null,
      },
    }
    conversationsResult = { data: [convNullCliente], error: null }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].cliente_nome).toBe('Sem nome')
  })

  it('returns chip as null when no chip linked', async () => {
    conversationsResult = { data: [sampleConversation], error: null }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].chip).toBeNull()
  })

  it('defaults to page 1 and per_page 50', async () => {
    const conversations = Array.from({ length: 60 }, (_, i) => ({
      ...sampleConversation,
      id: `conv-${i}`,
    }))
    conversationsResult = { data: conversations, error: null }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data).toHaveLength(50)
    expect(data.total).toBe(60)
    expect(data.pages).toBe(2)
  })

  // Sprint 64: New tests

  it('computes unread_count based on last message direction', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-1',
          conteudo: 'Oi Julia',
          autor_tipo: 'medico',
          created_at: '2024-01-10T10:00:00Z',
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    // Last message from medico (entrada) = 1 unread
    expect(data.data[0].unread_count).toBe(1)
  })

  it('sets unread_count to 0 when last message is outgoing', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-1',
          conteudo: 'Oi doutor!',
          autor_tipo: 'julia',
          created_at: '2024-01-10T10:00:00Z',
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].unread_count).toBe(0)
  })

  it('includes attention_reason for human-controlled conversations', async () => {
    const humanConv = { ...sampleConversation, controlled_by: 'human' }
    conversationsResult = { data: [humanConv], error: null }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].attention_reason).toBe('Handoff pendente')
  })

  it('includes handoff_reason as attention_reason when available', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    handoffsResult = {
      data: [
        {
          conversation_id: 'conv-1',
          motivo: 'Medico quer falar com humano',
          status: 'pendente',
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].attention_reason).toBe('Medico quer falar com humano')
  })

  it('attention_reason is null for normal AI conversations', async () => {
    conversationsResult = { data: [sampleConversation], error: null }
    interacoesResult = {
      data: [
        {
          conversation_id: 'conv-1',
          conteudo: 'Oi doutor!',
          autor_tipo: 'julia',
          created_at: new Date().toISOString(),
        },
      ],
      error: null,
    }

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].attention_reason).toBeNull()
  })
})
