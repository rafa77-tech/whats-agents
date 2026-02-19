/**
 * Testes para POST /api/conversas/[id]/discard
 * Sprint 64: Descartar contato
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { POST } from '@/app/api/conversas/[id]/discard/route'
import { NextRequest } from 'next/server'

// ---------- Supabase mock ----------

interface MockResult {
  data: unknown
  error: unknown
}

let selectResult: MockResult = { data: null, error: null }
let updateClienteResult: MockResult = { data: null, error: null }
let updateConversationResult: MockResult = { data: null, error: null }
let insertResult: MockResult = { data: null, error: null }

let updateCalls: { table: string; data: Record<string, unknown> }[] = []
let insertCalls: { table: string; data: Record<string, unknown> }[] = []

function makeSingleChain(resultGetter: () => MockResult) {
  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (prop === 'then') {
        return (
          onFulfilled?: (val: MockResult) => unknown,
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

const mockFrom = vi.fn((table: string) => {
  if (table === 'conversations') {
    // Could be select (first call) or update (later call)
    // We distinguish by the method called on it
    const handler: ProxyHandler<object> = {
      get(_target, prop) {
        if (prop === 'then') {
          return (
            onFulfilled?: (val: MockResult) => unknown,
            onRejected?: (reason: unknown) => unknown
          ) => {
            return Promise.resolve(selectResult).then(onFulfilled, onRejected)
          }
        }
        if (prop === 'select') {
          return vi.fn(() => makeSingleChain(() => selectResult))
        }
        if (prop === 'update') {
          return vi.fn((data: Record<string, unknown>) => {
            updateCalls.push({ table: 'conversations', data })
            return makeSingleChain(() => updateConversationResult)
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
  if (table === 'clientes') {
    const handler: ProxyHandler<object> = {
      get(_target, prop) {
        if (prop === 'then') {
          return (
            onFulfilled?: (val: MockResult) => unknown,
            onRejected?: (reason: unknown) => unknown
          ) => {
            return Promise.resolve(updateClienteResult).then(onFulfilled, onRejected)
          }
        }
        if (prop === 'update') {
          return vi.fn((data: Record<string, unknown>) => {
            updateCalls.push({ table: 'clientes', data })
            return makeSingleChain(() => updateClienteResult)
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
  if (table === 'business_events') {
    const handler: ProxyHandler<object> = {
      get(_target, prop) {
        if (prop === 'then') {
          return (
            onFulfilled?: (val: MockResult) => unknown,
            onRejected?: (reason: unknown) => unknown
          ) => {
            return Promise.resolve(insertResult).then(onFulfilled, onRejected)
          }
        }
        if (prop === 'insert') {
          return vi.fn((data: Record<string, unknown>) => {
            insertCalls.push({ table: 'business_events', data })
            return makeSingleChain(() => insertResult)
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
  return makeSingleChain(() => ({ data: null, error: null }))
})

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({ from: mockFrom }),
}))

// ---------- Helpers ----------

function createRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/conversas/conv-1/discard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

const makeParams = (id: string) => Promise.resolve({ id })

// ---------- Tests ----------

describe('POST /api/conversas/[id]/discard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    selectResult = {
      data: { id: 'conv-1', cliente_id: 'cli-1' },
      error: null,
    }
    updateClienteResult = { data: null, error: null }
    updateConversationResult = { data: null, error: null }
    insertResult = { data: null, error: null }
    updateCalls = []
    insertCalls = []
  })

  it('discards contact with valid reason', async () => {
    const request = createRequest({ reason: 'Nao e medico' })
    const response = await POST(request, { params: makeParams('conv-1') })
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockFrom).toHaveBeenCalledWith('conversations')
    expect(mockFrom).toHaveBeenCalledWith('clientes')
    expect(mockFrom).toHaveBeenCalledWith('business_events')
  })

  it('returns 400 when reason is missing', async () => {
    const request = createRequest({})
    const response = await POST(request, { params: makeParams('conv-1') })
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toBe('Motivo obrigatorio')
  })

  it('returns 400 when reason is empty string', async () => {
    const request = createRequest({ reason: '  ' })
    const response = await POST(request, { params: makeParams('conv-1') })
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toBe('Motivo obrigatorio')
  })

  it('returns 400 when reason is invalid', async () => {
    const request = createRequest({ reason: 'Motivo qualquer' })
    const response = await POST(request, { params: makeParams('conv-1') })
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toBe('Motivo invalido')
  })

  it('returns 404 when conversation not found', async () => {
    selectResult = { data: null, error: { code: 'PGRST116', message: 'Not found' } }

    const request = createRequest({ reason: 'Spam/Bot' })
    const response = await POST(request, { params: makeParams('conv-999') })
    const data = await response.json()

    expect(response.status).toBe(404)
    expect(data.error).toBe('Conversa nao encontrada')
  })

  it('accepts all valid reasons', async () => {
    const validReasons = ['Nao e medico', 'Spam/Bot', 'Numero errado', 'Outro']

    for (const reason of validReasons) {
      vi.clearAllMocks()
      selectResult = { data: { id: 'conv-1', cliente_id: 'cli-1' }, error: null }
      updateClienteResult = { data: null, error: null }
      updateConversationResult = { data: null, error: null }
      insertResult = { data: null, error: null }

      const request = createRequest({ reason })
      const response = await POST(request, { params: makeParams('conv-1') })
      expect(response.status).toBe(200)
    }
  })
})
