/**
 * Testes para GET /api/campanhas e POST /api/campanhas
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, POST } from '@/app/api/campanhas/route'
import { NextRequest } from 'next/server'

// Mock createClient (server-side Supabase, NOT createAdminClient)
// vi.hoisted ensures these are available when the hoisted vi.mock runs
const { mockFrom, mockAuth } = vi.hoisted(() => {
  const mockFrom = vi.fn()
  const mockAuth = { getUser: vi.fn() }
  return { mockFrom, mockAuth }
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({ from: mockFrom, auth: mockAuth }),
}))

// =====================================================================
// Helpers
// =====================================================================

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/campanhas?${searchParams}`
  return new NextRequest(url)
}

function createPostRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/campanhas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** Builds a chainable mock for campanhas query (GET).
 *  The chain is thenable (awaitable) at any point, but also supports
 *  further chaining like .in(). This mirrors the Supabase query builder. */
function mockCampanhasQuery(result: { data: unknown; error: unknown }) {
  const chain: Record<string, unknown> = {}
  const methods = ['select', 'order', 'limit', 'in']
  for (const m of methods) {
    chain[m] = vi.fn(() => chain)
  }
  // Make the chain thenable so `await query` resolves to result
  chain.then = (resolve: (v: unknown) => unknown) => resolve(result)
  return chain as Record<string, ReturnType<typeof vi.fn>> & { then: unknown }
}

/** Builds a chainable mock for envios query */
function mockEnviosQuery(result: { data: unknown; error?: unknown }) {
  const chain = {
    select: vi.fn().mockReturnThis(),
    in: vi.fn().mockResolvedValue(result),
  }
  return chain
}

/** Builds a chainable mock for fila_mensagens query */
function mockFilaMensagensQuery(result: { data: unknown; error?: unknown }) {
  const chain = {
    select: vi.fn().mockResolvedValue(result),
  }
  return chain
}

/** Builds a chainable mock for campanhas insert (POST) */
function mockInsertChain(result: { data: unknown; error: unknown }) {
  const chain = {
    insert: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
    single: vi.fn().mockResolvedValue(result),
  }
  return chain
}

/** Builds a chainable mock for audit_log insert */
function mockAuditInsert() {
  return {
    insert: vi.fn().mockResolvedValue({ data: null, error: null }),
  }
}

// =====================================================================
// GET /api/campanhas
// =====================================================================

describe('GET /api/campanhas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de campanhas com metricas calculadas', async () => {
    const campanhas = [
      {
        id: 1,
        nome_template: 'Campanha A',
        status: 'ativa',
        total_destinatarios: 10,
        enviados: 0,
        entregues: 0,
        respondidos: 0,
      },
      {
        id: 2,
        nome_template: 'Campanha B',
        status: 'rascunho',
        total_destinatarios: 5,
        enviados: 0,
        entregues: 0,
        respondidos: 0,
      },
    ]

    const campanhasChain = mockCampanhasQuery({ data: campanhas, error: null })
    const enviosChain = mockEnviosQuery({
      data: [
        {
          campanha_id: 1,
          enviado_em: '2026-01-01',
          entregue_em: '2026-01-01',
          visualizado_em: null,
          status: 'enviado',
        },
        {
          campanha_id: 1,
          enviado_em: '2026-01-01',
          entregue_em: null,
          visualizado_em: null,
          status: 'enviado',
        },
      ],
    })
    const filaChain = mockFilaMensagensQuery({ data: [] })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return campanhasChain
      if (table === 'envios') return enviosChain
      if (table === 'fila_mensagens') return filaChain
      return {}
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveLength(2)
    // Campanha A: 2 envios total, 2 enviados, 1 entregue
    expect(data[0].total_destinatarios).toBe(10) // stored > 0, so stored is used
    expect(data[0].enviados).toBe(2)
    expect(data[0].entregues).toBe(1)
  })

  it('deve filtrar por status quando parametro fornecido', async () => {
    const campanhas = [
      {
        id: 1,
        nome_template: 'Ativa',
        status: 'ativa',
        total_destinatarios: 0,
        enviados: 0,
        entregues: 0,
        respondidos: 0,
      },
    ]

    const campanhasChain = mockCampanhasQuery({ data: campanhas, error: null })
    const enviosChain = mockEnviosQuery({ data: [] })
    const filaChain = mockFilaMensagensQuery({ data: [] })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return campanhasChain
      if (table === 'envios') return enviosChain
      if (table === 'fila_mensagens') return filaChain
      return {}
    })

    const request = createRequest({ status: 'ativa,finalizada' })
    await GET(request)

    expect(campanhasChain.in).toHaveBeenCalledWith('status', ['ativa', 'finalizada'])
  })

  it('deve retornar array vazio quando nao ha campanhas', async () => {
    const campanhasChain = mockCampanhasQuery({ data: [], error: null })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return campanhasChain
      return {}
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve retornar array vazio quando campanhas e null', async () => {
    const campanhasChain = mockCampanhasQuery({ data: null, error: null })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return campanhasChain
      return {}
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve retornar erro 500 quando supabase retorna erro', async () => {
    const campanhasChain = mockCampanhasQuery({
      data: null,
      error: { message: 'DB connection failed' },
    })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return campanhasChain
      return {}
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao buscar campanhas')

    consoleSpy.mockRestore()
  })

  it('deve retornar erro 500 quando ocorre excecao inesperada', async () => {
    mockFrom.mockImplementation(() => {
      throw new Error('Unexpected')
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro interno do servidor')

    consoleSpy.mockRestore()
  })

  it('deve calcular metricas de fila_mensagens com deduplicacao por cliente', async () => {
    const campanhas = [
      {
        id: 10,
        nome_template: 'C',
        status: 'ativa',
        total_destinatarios: 0,
        enviados: 0,
        entregues: 0,
        respondidos: 0,
      },
    ]

    const campanhasChain = mockCampanhasQuery({ data: campanhas, error: null })
    const enviosChain = mockEnviosQuery({ data: [] })
    const filaChain = mockFilaMensagensQuery({
      data: [
        {
          id: 'f1',
          cliente_id: 'c1',
          status: 'enviada',
          enviada_em: '2026-01-01',
          outcome: null,
          metadata: { campanha_id: '10' },
        },
        // Duplicate cliente_id for same campanha - should be ignored
        {
          id: 'f2',
          cliente_id: 'c1',
          status: 'enviada',
          enviada_em: '2026-01-01',
          outcome: null,
          metadata: { campanha_id: '10' },
        },
        {
          id: 'f3',
          cliente_id: 'c2',
          status: 'pendente',
          enviada_em: null,
          outcome: null,
          metadata: { campanha_id: '10' },
        },
      ],
    })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return campanhasChain
      if (table === 'envios') return enviosChain
      if (table === 'fila_mensagens') return filaChain
      return {}
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    // 2 unique clients, not 3
    expect(data[0].total_destinatarios).toBe(2)
    // Only c1 was enviada
    expect(data[0].enviados).toBe(1)
    expect(data[0].entregues).toBe(1)
  })
})

// =====================================================================
// POST /api/campanhas
// =====================================================================

describe('POST /api/campanhas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve criar campanha com sucesso', async () => {
    const createdCampanha = {
      id: 99,
      nome_template: 'Campanha Nova',
      tipo_campanha: 'oferta_plantao',
      corpo: 'Oi doutor',
    }

    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const insertChain = mockInsertChain({ data: createdCampanha, error: null })
    const auditChain = mockAuditInsert()

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return insertChain
      if (table === 'audit_log') return auditChain
      return {}
    })

    const request = createPostRequest({
      nome_template: 'Campanha Nova',
      tipo_campanha: 'oferta_plantao',
      corpo: 'Oi doutor',
      tom: 'amigavel',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(201)
    expect(data.id).toBe(99)
    expect(data.nome_template).toBe('Campanha Nova')

    // Verify insert was called
    expect(insertChain.insert).toHaveBeenCalledWith(
      expect.objectContaining({
        nome_template: 'Campanha Nova',
        tipo_campanha: 'oferta_plantao',
        corpo: 'Oi doutor',
        tom: 'amigavel',
        created_by: 'test@example.com',
      })
    )
  })

  it('deve retornar 401 quando usuario nao autenticado', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: null },
    })

    const request = createPostRequest({
      nome_template: 'Test',
      corpo: 'Body',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.detail).toBe('Nao autorizado')
  })

  it('deve retornar 400 quando nome_template esta vazio', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const request = createPostRequest({
      nome_template: '',
      corpo: 'Body',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome da campanha e obrigatorio')
  })

  it('deve retornar 400 quando nome_template e apenas espacos', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const request = createPostRequest({
      nome_template: '   ',
      corpo: 'Body',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome da campanha e obrigatorio')
  })

  it('deve retornar 400 quando nome_template nao fornecido', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const request = createPostRequest({ corpo: 'Body' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome da campanha e obrigatorio')
  })

  it('deve retornar 400 quando corpo vazio para tipo oferta_plantao', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const request = createPostRequest({
      nome_template: 'Test',
      tipo_campanha: 'oferta_plantao',
      corpo: '',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Corpo da mensagem e obrigatorio')
  })

  it('deve retornar 400 quando corpo nao fornecido para tipo que exige mensagem customizada', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const request = createPostRequest({
      nome_template: 'Test',
      tipo_campanha: 'oferta_plantao',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Corpo da mensagem e obrigatorio')
  })

  it.each(['descoberta', 'reativacao', 'followup'])(
    'nao deve exigir corpo para tipo %s (mensagem automatica)',
    async (tipo) => {
      const createdCampanha = {
        id: 50,
        nome_template: `Campanha ${tipo}`,
        tipo_campanha: tipo,
        corpo: null,
      }

      mockAuth.getUser.mockResolvedValue({
        data: { user: { email: 'test@example.com' } },
      })

      const insertChain = mockInsertChain({ data: createdCampanha, error: null })
      const auditChain = mockAuditInsert()

      mockFrom.mockImplementation((table: string) => {
        if (table === 'campanhas') return insertChain
        if (table === 'audit_log') return auditChain
        return {}
      })

      const request = createPostRequest({
        nome_template: `Campanha ${tipo}`,
        tipo_campanha: tipo,
        corpo: '',
      })
      const response = await POST(request)

      expect(response.status).toBe(201)
    }
  )

  it('deve registrar entrada no audit_log ao criar campanha', async () => {
    const createdCampanha = {
      id: 42,
      nome_template: 'Auditada',
      tipo_campanha: 'oferta_plantao',
    }

    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'auditor@example.com' } },
    })

    const insertChain = mockInsertChain({ data: createdCampanha, error: null })
    const auditChain = mockAuditInsert()

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return insertChain
      if (table === 'audit_log') return auditChain
      return {}
    })

    const request = createPostRequest({
      nome_template: 'Auditada',
      tipo_campanha: 'oferta_plantao',
      corpo: 'Corpo',
    })
    await POST(request)

    expect(auditChain.insert).toHaveBeenCalledWith(
      expect.objectContaining({
        action: 'campanha_criada',
        user_email: 'auditor@example.com',
        details: {
          campanha_id: 42,
          nome: 'Auditada',
          tipo: 'oferta_plantao',
        },
      })
    )
  })

  it('deve retornar 500 quando supabase retorna erro ao inserir', async () => {
    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const insertChain = mockInsertChain({
      data: null,
      error: { message: 'Insert failed' },
    })

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return insertChain
      return {}
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createPostRequest({
      nome_template: 'Falha',
      tipo_campanha: 'oferta_plantao',
      corpo: 'Corpo',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao criar campanha')

    consoleSpy.mockRestore()
  })

  it('deve retornar 500 quando ocorre excecao inesperada', async () => {
    mockAuth.getUser.mockImplementation(() => {
      throw new Error('Unexpected auth error')
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createPostRequest({
      nome_template: 'Test',
      corpo: 'Body',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro interno do servidor')

    consoleSpy.mockRestore()
  })

  it('deve usar defaults quando campos opcionais nao fornecidos', async () => {
    const createdCampanha = {
      id: 77,
      nome_template: 'Minima',
      tipo_campanha: 'oferta_plantao',
    }

    mockAuth.getUser.mockResolvedValue({
      data: { user: { email: 'test@example.com' } },
    })

    const insertChain = mockInsertChain({ data: createdCampanha, error: null })
    const auditChain = mockAuditInsert()

    mockFrom.mockImplementation((table: string) => {
      if (table === 'campanhas') return insertChain
      if (table === 'audit_log') return auditChain
      return {}
    })

    const request = createPostRequest({
      nome_template: 'Minima',
      corpo: 'Corpo basico',
    })
    await POST(request)

    expect(insertChain.insert).toHaveBeenCalledWith(
      expect.objectContaining({
        tipo_campanha: 'oferta_plantao',
        categoria: 'marketing',
        tom: 'amigavel',
        status: 'rascunho',
        audience_filters: {},
        escopo_vagas: null,
        agendar_para: null,
        objetivo: null,
      })
    )
  })
})
