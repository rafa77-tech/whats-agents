/**
 * Tests for GET /api/dashboard/message-flow (Sprint 56)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/dashboard/message-flow/route'

// Chainable mock builder for supabase queries
function createQueryBuilder(data: unknown[] | null = [], error: unknown = null, count?: number) {
  const builder: Record<string, unknown> = {}
  const methods = ['select', 'from', 'in', 'order', 'limit', 'gte', 'eq']

  for (const method of methods) {
    builder[method] = vi.fn(() => builder)
  }
  builder.select = vi.fn((_cols?: string, opts?: { count?: string; head?: boolean }) => {
    if (opts?.head && opts?.count === 'exact') {
      // Return count-only result when resolved
      return {
        ...builder,
        then: (resolve: (val: { count: number }) => void) => resolve({ count: count ?? 0 }),
      } as unknown
    }
    return builder
  })
  // Final resolution
  Object.defineProperty(builder, 'then', {
    value: (resolve: (val: { data: unknown[] | null; error: unknown }) => void) =>
      resolve({ data, error }),
    writable: true,
    configurable: true,
  })

  return builder
}

const mockFrom = vi.fn()
const mockSupabase = { from: mockFrom }

vi.mock('@/lib/supabase/server', () => ({
  createClient: () => Promise.resolve(mockSupabase),
}))

describe('GET /api/dashboard/message-flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function setupMockQueries({
    chips = [] as unknown[],
    interacoes = [] as unknown[],
    chipsError = null as unknown,
    msgCount = 0,
  } = {}) {
    mockFrom.mockImplementation((table: string) => {
      if (table === 'chips') {
        return createQueryBuilder(chips, chipsError)
      }
      if (table === 'interacoes') {
        // Return different builders for different calls
        // The select with count+head returns count, others return data
        return createQueryBuilder(interacoes, null, msgCount)
      }
      return createQueryBuilder()
    })
  }

  it('retorna 200 com formato MessageFlowData', async () => {
    setupMockQueries({
      chips: [
        {
          id: 'c1',
          instance_name: 'Julia-01',
          status: 'active',
          trust_score: 85,
          msgs_enviadas_hoje: 10,
          msgs_recebidas_hoje: 5,
        },
      ],
      interacoes: [
        {
          id: 1,
          chip_id: 'c1',
          tipo: 'saida',
          created_at: new Date().toISOString(),
        },
      ],
      msgCount: 3,
    })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveProperty('chips')
    expect(data).toHaveProperty('recentMessages')
    expect(data).toHaveProperty('messagesPerMinute')
    expect(data).toHaveProperty('updatedAt')
    expect(Array.isArray(data.chips)).toBe(true)
    expect(Array.isArray(data.recentMessages)).toBe(true)
    expect(typeof data.messagesPerMinute).toBe('number')
  })

  it('retorna chips vazios quando nenhum chip ativo', async () => {
    setupMockQueries({ chips: [] })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.chips).toEqual([])
    expect(data.recentMessages).toEqual([])
  })

  it('mapeia status do banco para ChipNodeStatus corretamente', async () => {
    setupMockQueries({
      chips: [
        {
          id: 'c1',
          instance_name: 'A',
          status: 'active',
          trust_score: 90,
          msgs_enviadas_hoje: 0,
          msgs_recebidas_hoje: 0,
        },
        {
          id: 'c2',
          instance_name: 'B',
          status: 'warming',
          trust_score: 50,
          msgs_enviadas_hoje: 0,
          msgs_recebidas_hoje: 0,
        },
        {
          id: 'c3',
          instance_name: 'C',
          status: 'ready',
          trust_score: 60,
          msgs_enviadas_hoje: 0,
          msgs_recebidas_hoje: 0,
        },
        {
          id: 'c4',
          instance_name: 'D',
          status: 'degraded',
          trust_score: 30,
          msgs_enviadas_hoje: 0,
          msgs_recebidas_hoje: 0,
        },
        {
          id: 'c5',
          instance_name: 'E',
          status: 'paused',
          trust_score: 70,
          msgs_enviadas_hoje: 0,
          msgs_recebidas_hoje: 0,
        },
      ],
    })

    const response = await GET()
    const data = await response.json()

    expect(data.chips[0].status).toBe('active')
    expect(data.chips[1].status).toBe('warming')
    expect(data.chips[2].status).toBe('warming') // 'ready' maps to 'warming'
    expect(data.chips[3].status).toBe('degraded')
    expect(data.chips[4].status).toBe('paused')
  })

  it('chip.isActive = true quando tem mensagem recente', async () => {
    const now = new Date()
    setupMockQueries({
      chips: [
        {
          id: 'c1',
          instance_name: 'A',
          status: 'active',
          trust_score: 90,
          msgs_enviadas_hoje: 5,
          msgs_recebidas_hoje: 3,
        },
      ],
      interacoes: [{ id: 1, chip_id: 'c1', tipo: 'saida', created_at: now.toISOString() }],
    })

    const response = await GET()
    const data = await response.json()

    expect(data.chips[0].isActive).toBe(true)
  })

  it('mensagens recentes mapeiam direction corretamente', async () => {
    setupMockQueries({
      chips: [
        {
          id: 'c1',
          instance_name: 'A',
          status: 'active',
          trust_score: 90,
          msgs_enviadas_hoje: 0,
          msgs_recebidas_hoje: 0,
        },
      ],
      interacoes: [
        { id: 1, chip_id: 'c1', tipo: 'saida', created_at: new Date().toISOString() },
        { id: 2, chip_id: 'c1', tipo: 'entrada', created_at: new Date().toISOString() },
      ],
    })

    const response = await GET()
    const data = await response.json()

    expect(data.recentMessages[0].direction).toBe('outbound')
    expect(data.recentMessages[1].direction).toBe('inbound')
  })

  it('retorna 500 em caso de erro no banco', async () => {
    setupMockQueries({ chipsError: new Error('DB connection failed') })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data).toHaveProperty('error')
  })

  it('messagesPerMinute é number >= 0', async () => {
    setupMockQueries({ msgCount: 7 })

    const response = await GET()
    const data = await response.json()

    expect(typeof data.messagesPerMinute).toBe('number')
    expect(data.messagesPerMinute).toBeGreaterThanOrEqual(0)
  })

  it('updatedAt é timestamp ISO válido', async () => {
    setupMockQueries()

    const response = await GET()
    const data = await response.json()

    const parsed = new Date(data.updatedAt)
    expect(parsed.toISOString()).toBe(data.updatedAt)
  })
})
