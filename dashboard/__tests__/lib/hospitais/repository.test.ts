/**
 * Testes para lib/hospitais/repository.ts
 */

import { describe, it, expect, vi } from 'vitest'
import {
  listarHospitaisBloqueados,
  listarHospitais,
  verificarHospitalExiste,
  verificarHospitalBloqueado,
  contarVagasAbertas,
  contarVagasBloqueadas,
  bloquearHospital,
  desbloquearHospital,
  registrarAuditLog,
} from '@/lib/hospitais/repository'

// =============================================================================
// Helper para criar mock do Supabase com chain adequado
// =============================================================================

function createChainableMock(finalResult: unknown) {
  const mock: Record<string, ReturnType<typeof vi.fn>> = {}

  const createChainable = (): unknown => {
    return new Proxy(
      {},
      {
        get: (_target, prop) => {
          if (prop === 'then') {
            // Se for thenable, resolve com o resultado final
            return (resolve: (value: unknown) => void) => resolve(finalResult)
          }
          // Retorna um mock que também é chainable
          if (!mock[prop as string]) {
            mock[prop as string] = vi.fn(() => createChainable())
          }
          return mock[prop as string]
        },
      }
    )
  }

  return { chainable: createChainable(), mocks: mock }
}

function createMockSupabase(fromResults: Record<string, unknown>) {
  const fromMock = vi.fn((table: string) => {
    const result = fromResults[table] || { data: null, error: null }
    return createChainableMock(result).chainable
  })

  return { from: fromMock } as unknown as Parameters<typeof listarHospitaisBloqueados>[0]
}

// =============================================================================
// listarHospitaisBloqueados
// =============================================================================

describe('listarHospitaisBloqueados', () => {
  it('deve listar apenas bloqueados ativos por padrao', async () => {
    const mockData = [
      {
        id: '1',
        hospital_id: 'h1',
        motivo: 'Pagamento atrasado',
        status: 'bloqueado',
        hospitais: { nome: 'Hospital A', cidade: 'SP' },
      },
    ]

    const supabase = createMockSupabase({
      hospitais_bloqueados: { data: mockData, error: null },
    })

    const result = await listarHospitaisBloqueados(supabase)

    expect(supabase.from).toHaveBeenCalledWith('hospitais_bloqueados')
    expect(result).toEqual(mockData)
  })

  it('deve incluir historico quando solicitado', async () => {
    const mockData = [
      { id: '1', status: 'bloqueado' },
      { id: '2', status: 'desbloqueado' },
    ]

    const supabase = createMockSupabase({
      hospitais_bloqueados: { data: mockData, error: null },
    })

    const result = await listarHospitaisBloqueados(supabase, { incluirHistorico: true })

    expect(result).toHaveLength(2)
  })

  it('deve lancar erro quando query falha', async () => {
    const supabase = createMockSupabase({
      hospitais_bloqueados: { data: null, error: { message: 'DB Error' } },
    })

    await expect(listarHospitaisBloqueados(supabase)).rejects.toThrow(
      'Erro ao buscar hospitais bloqueados: DB Error'
    )
  })

  it('deve retornar array vazio quando nao ha dados', async () => {
    const supabase = createMockSupabase({
      hospitais_bloqueados: { data: null, error: null },
    })

    const result = await listarHospitaisBloqueados(supabase)

    expect(result).toEqual([])
  })
})

// =============================================================================
// listarHospitais
// =============================================================================

describe('listarHospitais', () => {
  it('deve listar hospitais ativos', async () => {
    const mockHospitais = [
      { id: 'h1', nome: 'Hospital A', cidade: 'SP' },
      { id: 'h2', nome: 'Hospital B', cidade: 'RJ' },
    ]

    // Mock com resultados diferentes por tabela
    let callCount = 0
    const fromMock = vi.fn((table: string) => {
      callCount++
      let result: unknown

      if (table === 'hospitais') {
        result = { data: mockHospitais, error: null }
      } else if (table === 'vagas') {
        result = { data: [{ hospital_id: 'h1' }], error: null }
      } else {
        result = { data: [], error: null }
      }

      return createChainableMock(result).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof listarHospitais>[0]

    const result = await listarHospitais(supabase)

    expect(fromMock).toHaveBeenCalledWith('hospitais')
    expect(result).toHaveLength(2)
    expect(result[0]?.vagas_abertas).toBe(1)
    expect(result[1]?.vagas_abertas).toBe(0)
  })

  it('deve excluir bloqueados quando solicitado', async () => {
    const mockHospitais = [
      { id: 'h1', nome: 'Hospital A', cidade: 'SP' },
      { id: 'h2', nome: 'Hospital B', cidade: 'RJ' },
    ]
    const mockBloqueados = [{ hospital_id: 'h1' }]

    const fromMock = vi.fn((table: string) => {
      let result: unknown

      if (table === 'hospitais') {
        result = { data: mockHospitais, error: null }
      } else if (table === 'hospitais_bloqueados') {
        result = { data: mockBloqueados, error: null }
      } else if (table === 'vagas') {
        result = { data: [], error: null }
      } else {
        result = { data: [], error: null }
      }

      return createChainableMock(result).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof listarHospitais>[0]

    const result = await listarHospitais(supabase, { excluirBloqueados: true })

    // Deve filtrar h1 que esta bloqueado
    expect(result).toHaveLength(1)
    expect(result[0]?.id).toBe('h2')
  })

  it('deve lancar erro quando query falha', async () => {
    const supabase = createMockSupabase({
      hospitais: { data: null, error: { message: 'DB Error' } },
    })

    await expect(listarHospitais(supabase)).rejects.toThrow('Erro ao buscar hospitais: DB Error')
  })
})

// =============================================================================
// verificarHospitalExiste
// =============================================================================

describe('verificarHospitalExiste', () => {
  it('deve retornar existe=true quando hospital existe', async () => {
    const mockHospital = { id: 'h1', nome: 'Hospital A' }

    const supabase = createMockSupabase({
      hospitais: { data: mockHospital, error: null },
    })

    const result = await verificarHospitalExiste(supabase, 'h1')

    expect(result.existe).toBe(true)
    expect(result.hospital).toEqual(mockHospital)
  })

  it('deve retornar existe=false quando hospital nao existe', async () => {
    const supabase = createMockSupabase({
      hospitais: { data: null, error: { code: 'PGRST116' } },
    })

    const result = await verificarHospitalExiste(supabase, 'h999')

    expect(result.existe).toBe(false)
    expect(result.hospital).toBeUndefined()
  })
})

// =============================================================================
// verificarHospitalBloqueado
// =============================================================================

describe('verificarHospitalBloqueado', () => {
  it('deve retornar bloqueado=true quando hospital esta bloqueado', async () => {
    const mockBloqueio = {
      id: 'b1',
      hospital_id: 'h1',
      motivo: 'Teste',
      status: 'bloqueado',
    }

    const supabase = createMockSupabase({
      hospitais_bloqueados: { data: mockBloqueio, error: null },
    })

    const result = await verificarHospitalBloqueado(supabase, 'h1')

    expect(result.bloqueado).toBe(true)
    expect(result.bloqueio?.id).toBe('b1')
  })

  it('deve retornar bloqueado=false quando hospital nao esta bloqueado', async () => {
    const supabase = createMockSupabase({
      hospitais_bloqueados: { data: null, error: null },
    })

    const result = await verificarHospitalBloqueado(supabase, 'h1')

    expect(result.bloqueado).toBe(false)
    expect(result.bloqueio).toBeUndefined()
  })
})

// =============================================================================
// contarVagasAbertas
// =============================================================================

describe('contarVagasAbertas', () => {
  it('deve retornar contagem de vagas abertas', async () => {
    const supabase = createMockSupabase({
      vagas: { count: 5, error: null },
    })

    const result = await contarVagasAbertas(supabase, 'h1')

    expect(supabase.from).toHaveBeenCalledWith('vagas')
    expect(result).toBe(5)
  })

  it('deve retornar 0 quando nao ha vagas', async () => {
    const supabase = createMockSupabase({
      vagas: { count: null, error: null },
    })

    const result = await contarVagasAbertas(supabase, 'h1')

    expect(result).toBe(0)
  })
})

// =============================================================================
// contarVagasBloqueadas
// =============================================================================

describe('contarVagasBloqueadas', () => {
  it('deve retornar contagem de vagas bloqueadas', async () => {
    const supabase = createMockSupabase({
      vagas: { count: 3, error: null },
    })

    const result = await contarVagasBloqueadas(supabase, 'h1')

    expect(result).toBe(3)
  })
})

// =============================================================================
// bloquearHospital
// =============================================================================

describe('bloquearHospital', () => {
  it('deve bloquear hospital e atualizar vagas', async () => {
    // Mock complexo com múltiplas chamadas
    let vagasCallCount = 0
    const fromMock = vi.fn((table: string) => {
      if (table === 'vagas') {
        vagasCallCount++
        if (vagasCallCount === 1) {
          // Primeira chamada: count
          return createChainableMock({ count: 2, error: null }).chainable
        } else {
          // Segunda chamada: update
          return createChainableMock({ error: null }).chainable
        }
      } else if (table === 'hospitais_bloqueados') {
        return createChainableMock({ error: null }).chainable
      }
      return createChainableMock({ error: null }).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof bloquearHospital>[0]

    const result = await bloquearHospital(supabase, 'h1', 'Motivo teste', 'user@test.com')

    expect(result.success).toBe(true)
    expect(result.vagas_movidas).toBe(2)
  })

  it('deve lancar erro quando insert falha', async () => {
    let vagasCallCount = 0
    const fromMock = vi.fn((table: string) => {
      if (table === 'vagas') {
        vagasCallCount++
        return createChainableMock({ count: 0, error: null }).chainable
      } else if (table === 'hospitais_bloqueados') {
        return createChainableMock({ error: { message: 'Insert failed' } }).chainable
      }
      return createChainableMock({ error: null }).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof bloquearHospital>[0]

    await expect(bloquearHospital(supabase, 'h1', 'Motivo', 'user@test.com')).rejects.toThrow(
      'Erro ao bloquear hospital: Insert failed'
    )
  })

  it('deve nao atualizar vagas quando nao ha vagas abertas', async () => {
    const fromMock = vi.fn((table: string) => {
      if (table === 'vagas') {
        return createChainableMock({ count: 0, error: null }).chainable
      } else if (table === 'hospitais_bloqueados') {
        return createChainableMock({ error: null }).chainable
      }
      return createChainableMock({ error: null }).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof bloquearHospital>[0]

    const result = await bloquearHospital(supabase, 'h1', 'Motivo', 'user@test.com')

    expect(result.vagas_movidas).toBe(0)
  })
})

// =============================================================================
// desbloquearHospital
// =============================================================================

describe('desbloquearHospital', () => {
  it('deve desbloquear hospital e restaurar vagas', async () => {
    let vagasCallCount = 0
    const fromMock = vi.fn((table: string) => {
      if (table === 'hospitais_bloqueados') {
        return createChainableMock({ error: null }).chainable
      } else if (table === 'vagas') {
        vagasCallCount++
        if (vagasCallCount === 1) {
          return createChainableMock({ count: 3, error: null }).chainable
        }
        return createChainableMock({ error: null }).chainable
      }
      return createChainableMock({ error: null }).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof desbloquearHospital>[0]

    const result = await desbloquearHospital(supabase, 'h1', 'b1', 'user@test.com')

    expect(result.success).toBe(true)
    expect(result.vagas_restauradas).toBe(3)
  })

  it('deve lancar erro quando update falha', async () => {
    const supabase = createMockSupabase({
      hospitais_bloqueados: { error: { message: 'Update failed' } },
    })

    await expect(desbloquearHospital(supabase, 'h1', 'b1', 'user@test.com')).rejects.toThrow(
      'Erro ao desbloquear hospital: Update failed'
    )
  })

  it('deve nao restaurar vagas quando nao ha vagas bloqueadas', async () => {
    const fromMock = vi.fn((table: string) => {
      if (table === 'hospitais_bloqueados') {
        return createChainableMock({ error: null }).chainable
      } else if (table === 'vagas') {
        return createChainableMock({ count: 0, error: null }).chainable
      }
      return createChainableMock({ error: null }).chainable
    })

    const supabase = { from: fromMock } as unknown as Parameters<typeof desbloquearHospital>[0]

    const result = await desbloquearHospital(supabase, 'h1', 'b1', 'user@test.com')

    expect(result.vagas_restauradas).toBe(0)
  })
})

// =============================================================================
// registrarAuditLog
// =============================================================================

describe('registrarAuditLog', () => {
  it('deve inserir registro no audit_log', async () => {
    const supabase = createMockSupabase({
      audit_log: { error: null },
    })

    await registrarAuditLog(supabase, 'hospital_bloqueado', 'user@test.com', {
      hospital_id: 'h1',
      motivo: 'Teste',
    })

    expect(supabase.from).toHaveBeenCalledWith('audit_log')
  })
})
