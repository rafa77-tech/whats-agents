/**
 * Testes - API Market Intelligence Vagas Hoje
 */

import { GET } from '@/app/api/market-intelligence/vagas-hoje/route'
import { createClient } from '@/lib/supabase/server'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(),
}))

// Proxy-based chainable mock that resolves any chain to the final result
function makeChain(finalResult: unknown) {
  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (prop === 'then') {
        // Make it thenable — resolves to finalResult
        return (resolve: (v: unknown) => void) => resolve(finalResult)
      }
      // Any method call returns the proxy again
      return () => new Proxy({}, handler)
    },
  }
  return new Proxy({}, handler)
}

interface MockConfig {
  rpcResult?: { data: unknown; error: unknown }
  fromResults?: Array<{ data: unknown; error: unknown }>
}

function createSupabaseMock(config: MockConfig) {
  const {
    rpcResult = { data: null, error: { message: 'not found' } },
    fromResults = [],
  } = config

  let fromCallIndex = 0

  return {
    rpc: () => {
      // rpc returns a thenable
      return {
        then: (resolve: (v: unknown) => void) => resolve(rpcResult),
      }
    },
    from: () => {
      const result = fromResults[fromCallIndex] ?? { data: [], error: null }
      fromCallIndex++
      return makeChain(result)
    },
  }
}

describe('API /api/market-intelligence/vagas-hoje', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar 200 com estrutura correta (RPC ok, sem vagas)', async () => {
    const mock = createSupabaseMock({
      rpcResult: { data: [], error: null },
      fromResults: [{ data: [], error: null }], // vagas query
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    expect(response.status).toBe(200)

    const data = await response.json()
    expect(data).toHaveProperty('grupos')
    expect(data).toHaveProperty('vagas')
    expect(Array.isArray(data.grupos)).toBe(true)
    expect(Array.isArray(data.vagas)).toBe(true)
  })

  it('deve usar dados da RPC quando disponivel', async () => {
    const grupos = [
      { id: 'g1', nome: 'Grupo A', vagas_importadas: 10 },
      { id: 'g2', nome: 'Grupo B', vagas_importadas: 5 },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: grupos, error: null },
      fromResults: [{ data: [], error: null }],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.grupos).toHaveLength(2)
    expect(data.grupos[0].nome).toBe('Grupo A')
    expect(data.grupos[1].vagas_importadas).toBe(5)
  })

  it('deve fazer fallback para query direta quando RPC falha', async () => {
    const fallbackRows = [
      {
        grupo_origem_id: 'g1',
        grupos_whatsapp: { id: 'g1', nome: 'Grupo Fallback', ativo: true },
      },
      {
        grupo_origem_id: 'g1',
        grupos_whatsapp: { id: 'g1', nome: 'Grupo Fallback', ativo: true },
      },
      {
        grupo_origem_id: 'g2',
        grupos_whatsapp: { id: 'g2', nome: 'Outro Grupo', ativo: true },
      },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: null, error: { message: 'function not found' } },
      fromResults: [
        { data: fallbackRows, error: null }, // grupos fallback
        { data: [], error: null }, // vagas
      ],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.grupos).toHaveLength(2)
    const grupoFallback = data.grupos.find(
      (g: { nome: string }) => g.nome === 'Grupo Fallback'
    )
    expect(grupoFallback.vagas_importadas).toBe(2)
  })

  it('deve filtrar grupos inativos no fallback', async () => {
    const rows = [
      { grupo_origem_id: 'g1', grupos_whatsapp: { id: 'g1', nome: 'Ativo', ativo: true } },
      { grupo_origem_id: 'g2', grupos_whatsapp: { id: 'g2', nome: 'Inativo', ativo: false } },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: null, error: { message: 'err' } },
      fromResults: [
        { data: rows, error: null },
        { data: [], error: null },
      ],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.grupos).toHaveLength(1)
    expect(data.grupos[0].nome).toBe('Ativo')
  })

  it('deve mapear vagas com mensagem_original quando presente', async () => {
    const vagas = [
      {
        id: 'v1',
        hospital_raw: 'Hospital ABC',
        especialidade_raw: 'Cardio',
        valor: 2000,
        data: '2024-01-15',
        periodo: 'noturno',
        created_at: '2024-01-15T10:00:00Z',
        grupo_origem_id: 'g1',
        mensagem_id: 'm1',
        grupos_whatsapp: { nome: 'Grupo A' },
        mensagens_grupo: {
          texto: 'Vaga disponivel',
          sender_nome: 'Joao',
          created_at: '2024-01-15T09:00:00Z',
        },
      },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: [], error: null },
      fromResults: [{ data: vagas, error: null }],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.vagas).toHaveLength(1)
    expect(data.vagas[0].hospital).toBe('Hospital ABC')
    expect(data.vagas[0].grupo).toBe('Grupo A')
    expect(data.vagas[0].mensagem_original).toEqual({
      texto: 'Vaga disponivel',
      sender_nome: 'Joao',
      created_at: '2024-01-15T09:00:00Z',
    })
  })

  it('deve retornar mensagem_original null quando nao tem mensagem', async () => {
    const vagas = [
      {
        id: 'v1',
        hospital_raw: 'Hospital XYZ',
        especialidade_raw: 'Ortopedia',
        valor: null,
        data: null,
        periodo: null,
        created_at: '2024-01-15T10:00:00Z',
        grupo_origem_id: 'g1',
        mensagem_id: null,
        grupos_whatsapp: { nome: 'Grupo B' },
        mensagens_grupo: null,
      },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: [], error: null },
      fromResults: [{ data: vagas, error: null }],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.vagas).toHaveLength(1)
    expect(data.vagas[0].mensagem_original).toBeNull()
  })

  it('deve retornar grupo "-" quando grupos_whatsapp e null', async () => {
    const vagas = [
      {
        id: 'v1',
        hospital_raw: 'Hosp',
        especialidade_raw: 'Esp',
        valor: null,
        data: null,
        periodo: null,
        created_at: '2024-01-15T10:00:00Z',
        grupo_origem_id: null,
        mensagem_id: null,
        grupos_whatsapp: null,
        mensagens_grupo: null,
      },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: [], error: null },
      fromResults: [{ data: vagas, error: null }],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.vagas[0].grupo).toBe('-')
  })

  it('deve retornar 500 quando query de grupos fallback falha', async () => {
    const mock = createSupabaseMock({
      rpcResult: { data: null, error: { message: 'rpc fail' } },
      fromResults: [{ data: null, error: { message: 'db error' } }],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    expect(response.status).toBe(500)
  })

  it('deve retornar 500 quando query de vagas falha', async () => {
    const mock = createSupabaseMock({
      rpcResult: { data: [], error: null },
      fromResults: [{ data: null, error: { message: 'db error' } }],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    expect(response.status).toBe(500)
  })

  it('deve ordenar grupos por vagas_importadas desc no fallback', async () => {
    const rows = [
      { grupo_origem_id: 'g1', grupos_whatsapp: { id: 'g1', nome: 'Pouco', ativo: true } },
      { grupo_origem_id: 'g2', grupos_whatsapp: { id: 'g2', nome: 'Muito', ativo: true } },
      { grupo_origem_id: 'g2', grupos_whatsapp: { id: 'g2', nome: 'Muito', ativo: true } },
      { grupo_origem_id: 'g2', grupos_whatsapp: { id: 'g2', nome: 'Muito', ativo: true } },
    ]
    const mock = createSupabaseMock({
      rpcResult: { data: null, error: { message: 'err' } },
      fromResults: [
        { data: rows, error: null },
        { data: [], error: null },
      ],
    })
    vi.mocked(createClient).mockResolvedValue(mock as never)

    const response = await GET()
    const data = await response.json()

    expect(data.grupos[0].nome).toBe('Muito')
    expect(data.grupos[0].vagas_importadas).toBe(3)
    expect(data.grupos[1].nome).toBe('Pouco')
    expect(data.grupos[1].vagas_importadas).toBe(1)
  })
})
