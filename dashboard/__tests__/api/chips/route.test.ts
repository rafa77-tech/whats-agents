/**
 * Testes para GET /api/chips
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/chips/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient (sync, returns supabase directly)
const mockFrom = vi.fn()

const mockSupabase = { from: mockFrom }

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest() {
  return new NextRequest('http://localhost:3000/api/chips')
}

// Helper to setup the two chained supabase calls (chips + conversation_chips)
function setupMocks(
  chipsResult: { data: unknown[] | null; error: unknown },
  conversationResult: { data: unknown[] | null; error?: unknown }
) {
  mockFrom.mockImplementation((table: string) => {
    if (table === 'chips') {
      return {
        select: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            order: vi.fn().mockResolvedValue(chipsResult),
          }),
        }),
      }
    }
    if (table === 'conversation_chips') {
      return {
        select: vi.fn().mockReturnValue({
          in: vi.fn().mockReturnValue({
            eq: vi.fn().mockResolvedValue(conversationResult),
          }),
        }),
      }
    }
    return {}
  })
}

describe('GET /api/chips', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de chips com contagem de conversas', async () => {
    const chips = [
      {
        id: 'chip-1',
        telefone: '5511999990001',
        instance_name: 'julia-01',
        status: 'active',
        trust_level: 5,
        pode_prospectar: true,
        msgs_enviadas_hoje: 10,
        msgs_recebidas_hoje: 8,
      },
      {
        id: 'chip-2',
        telefone: '5511999990002',
        instance_name: 'julia-02',
        status: 'warming',
        trust_level: 3,
        pode_prospectar: false,
        msgs_enviadas_hoje: 5,
        msgs_recebidas_hoje: 3,
      },
    ]

    const conversations = [{ chip_id: 'chip-1' }, { chip_id: 'chip-1' }, { chip_id: 'chip-2' }]

    setupMocks({ data: chips, error: null }, { data: conversations })

    const response = await GET(createRequest())
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data).toHaveLength(2)
    expect(body.data[0].conversation_count).toBe(2)
    expect(body.data[1].conversation_count).toBe(1)
  })

  it('deve retornar data vazio quando nao ha chips', async () => {
    setupMocks({ data: [], error: null }, { data: [] })

    const response = await GET(createRequest())
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data).toEqual([])
  })

  it('deve retornar conversation_count 0 para chip sem conversas', async () => {
    const chips = [
      {
        id: 'chip-1',
        telefone: '5511999990001',
        instance_name: 'julia-01',
        status: 'active',
        trust_level: 5,
        pode_prospectar: true,
        msgs_enviadas_hoje: 10,
        msgs_recebidas_hoje: 8,
      },
    ]

    setupMocks({ data: chips, error: null }, { data: [] })

    const response = await GET(createRequest())
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data[0].conversation_count).toBe(0)
  })

  it('deve retornar { data: [] } quando supabase retorna erro', async () => {
    setupMocks({ data: null, error: { message: 'DB error' } }, { data: [] })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const response = await GET(createRequest())
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data).toEqual([])

    consoleSpy.mockRestore()
  })

  it('deve contar multiplas conversas corretamente por chip', async () => {
    const chips = [
      {
        id: 'chip-a',
        telefone: '5511999990001',
        instance_name: 'julia-a',
        status: 'ready',
        trust_level: 4,
        pode_prospectar: true,
        msgs_enviadas_hoje: 20,
        msgs_recebidas_hoje: 15,
      },
      {
        id: 'chip-b',
        telefone: '5511999990002',
        instance_name: 'julia-b',
        status: 'active',
        trust_level: 5,
        pode_prospectar: true,
        msgs_enviadas_hoje: 30,
        msgs_recebidas_hoje: 25,
      },
    ]

    const conversations = [
      { chip_id: 'chip-a' },
      { chip_id: 'chip-a' },
      { chip_id: 'chip-a' },
      { chip_id: 'chip-b' },
      { chip_id: 'chip-b' },
      { chip_id: 'chip-b' },
      { chip_id: 'chip-b' },
      { chip_id: 'chip-b' },
    ]

    setupMocks({ data: chips, error: null }, { data: conversations })

    const response = await GET(createRequest())
    const body = await response.json()

    expect(body.data[0].conversation_count).toBe(3)
    expect(body.data[1].conversation_count).toBe(5)
  })

  it('deve mapear campos do chip corretamente', async () => {
    const chips = [
      {
        id: 'chip-xyz',
        telefone: '5511888887777',
        instance_name: 'julia-prod-03',
        status: 'warming',
        trust_level: 2,
        pode_prospectar: false,
        msgs_enviadas_hoje: null,
        msgs_recebidas_hoje: null,
      },
    ]

    setupMocks({ data: chips, error: null }, { data: [] })

    const response = await GET(createRequest())
    const body = await response.json()

    const chip = body.data[0]
    expect(chip.id).toBe('chip-xyz')
    expect(chip.telefone).toBe('5511888887777')
    expect(chip.instance_name).toBe('julia-prod-03')
    expect(chip.status).toBe('warming')
    expect(chip.trust_level).toBe(2)
    expect(chip.pode_prospectar).toBe(false)
    expect(chip.msgs_enviadas_hoje).toBe(0)
    expect(chip.msgs_recebidas_hoje).toBe(0)
    expect(chip.conversation_count).toBe(0)
  })
})
