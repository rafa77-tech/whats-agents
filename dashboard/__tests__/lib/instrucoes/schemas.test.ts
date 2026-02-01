/**
 * Testes para lib/instrucoes/schemas.ts
 */

import { describe, it, expect } from 'vitest'
import {
  tipoDiretrizSchema,
  escopoSchema,
  statusSchema,
  diretrizConteudoSchema,
  diretrizesQuerySchema,
  parseDiretrizesQuery,
  criarDiretrizSchema,
  cancelarDiretrizSchema,
} from '@/lib/instrucoes/schemas'

// =============================================================================
// tipoDiretrizSchema
// =============================================================================

describe('tipoDiretrizSchema', () => {
  it('deve aceitar margem_negociacao', () => {
    expect(tipoDiretrizSchema.parse('margem_negociacao')).toBe('margem_negociacao')
  })

  it('deve aceitar regra_especial', () => {
    expect(tipoDiretrizSchema.parse('regra_especial')).toBe('regra_especial')
  })

  it('deve aceitar info_adicional', () => {
    expect(tipoDiretrizSchema.parse('info_adicional')).toBe('info_adicional')
  })

  it('deve rejeitar tipo invalido', () => {
    expect(() => tipoDiretrizSchema.parse('outro')).toThrow()
  })
})

// =============================================================================
// escopoSchema
// =============================================================================

describe('escopoSchema', () => {
  it('deve aceitar vaga', () => {
    expect(escopoSchema.parse('vaga')).toBe('vaga')
  })

  it('deve aceitar medico', () => {
    expect(escopoSchema.parse('medico')).toBe('medico')
  })

  it('deve aceitar hospital', () => {
    expect(escopoSchema.parse('hospital')).toBe('hospital')
  })

  it('deve aceitar especialidade', () => {
    expect(escopoSchema.parse('especialidade')).toBe('especialidade')
  })

  it('deve aceitar global', () => {
    expect(escopoSchema.parse('global')).toBe('global')
  })

  it('deve rejeitar escopo invalido', () => {
    expect(() => escopoSchema.parse('outro')).toThrow()
  })
})

// =============================================================================
// statusSchema
// =============================================================================

describe('statusSchema', () => {
  it('deve aceitar ativa', () => {
    expect(statusSchema.parse('ativa')).toBe('ativa')
  })

  it('deve aceitar expirada', () => {
    expect(statusSchema.parse('expirada')).toBe('expirada')
  })

  it('deve aceitar cancelada', () => {
    expect(statusSchema.parse('cancelada')).toBe('cancelada')
  })

  it('deve rejeitar status invalido', () => {
    expect(() => statusSchema.parse('pendente')).toThrow()
  })
})

// =============================================================================
// diretrizConteudoSchema
// =============================================================================

describe('diretrizConteudoSchema', () => {
  it('deve aceitar valor_maximo', () => {
    const result = diretrizConteudoSchema.parse({ valor_maximo: 3000 })
    expect(result.valor_maximo).toBe(3000)
  })

  it('deve aceitar percentual_maximo', () => {
    const result = diretrizConteudoSchema.parse({ percentual_maximo: 15 })
    expect(result.percentual_maximo).toBe(15)
  })

  it('deve aceitar regra', () => {
    const result = diretrizConteudoSchema.parse({ regra: 'Regra de teste' })
    expect(result.regra).toBe('Regra de teste')
  })

  it('deve aceitar info', () => {
    const result = diretrizConteudoSchema.parse({ info: 'Info de teste' })
    expect(result.info).toBe('Info de teste')
  })

  it('deve aceitar objeto vazio', () => {
    const result = diretrizConteudoSchema.parse({})
    expect(result).toEqual({})
  })

  it('deve rejeitar valor_maximo negativo', () => {
    expect(() => diretrizConteudoSchema.parse({ valor_maximo: -100 })).toThrow()
  })

  it('deve rejeitar percentual_maximo acima de 100', () => {
    expect(() => diretrizConteudoSchema.parse({ percentual_maximo: 150 })).toThrow()
  })

  it('deve rejeitar regra vazia', () => {
    expect(() => diretrizConteudoSchema.parse({ regra: '' })).toThrow()
  })
})

// =============================================================================
// diretrizesQuerySchema
// =============================================================================

describe('diretrizesQuerySchema', () => {
  it('deve usar default ativa quando status nao informado', () => {
    const result = diretrizesQuerySchema.parse({})
    expect(result.status).toBe('ativa')
  })

  it('deve aceitar status customizado', () => {
    const result = diretrizesQuerySchema.parse({ status: 'expirada,cancelada' })
    expect(result.status).toBe('expirada,cancelada')
  })
})

// =============================================================================
// parseDiretrizesQuery
// =============================================================================

describe('parseDiretrizesQuery', () => {
  it('deve parsear status dos search params', () => {
    const params = new URLSearchParams('status=ativa')
    const result = parseDiretrizesQuery(params)
    expect(result.status).toBe('ativa')
  })

  it('deve usar default quando status ausente', () => {
    const params = new URLSearchParams()
    const result = parseDiretrizesQuery(params)
    expect(result.status).toBe('ativa')
  })

  it('deve parsear multiplos status', () => {
    const params = new URLSearchParams('status=expirada,cancelada')
    const result = parseDiretrizesQuery(params)
    expect(result.status).toBe('expirada,cancelada')
  })
})

// =============================================================================
// criarDiretrizSchema
// =============================================================================

describe('criarDiretrizSchema', () => {
  it('deve aceitar diretriz global de margem com valor_maximo', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
    })
    expect(result.tipo).toBe('margem_negociacao')
    expect(result.escopo).toBe('global')
  })

  it('deve aceitar diretriz global de margem com percentual', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { percentual_maximo: 15 },
    })
    expect(result.conteudo.percentual_maximo).toBe(15)
  })

  it('deve aceitar diretriz de regra especial', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'regra_especial',
      escopo: 'global',
      conteudo: { regra: 'Regra de teste' },
    })
    expect(result.conteudo.regra).toBe('Regra de teste')
  })

  it('deve aceitar diretriz de info adicional', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'info_adicional',
      escopo: 'global',
      conteudo: { info: 'Info de teste' },
    })
    expect(result.conteudo.info).toBe('Info de teste')
  })

  it('deve aceitar diretriz de hospital com hospital_id', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'margem_negociacao',
      escopo: 'hospital',
      hospital_id: '123e4567-e89b-12d3-a456-426614174000',
      conteudo: { valor_maximo: 5000 },
    })
    expect(result.hospital_id).toBe('123e4567-e89b-12d3-a456-426614174000')
  })

  it('deve aceitar diretriz de especialidade com especialidade_id', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'regra_especial',
      escopo: 'especialidade',
      especialidade_id: '123e4567-e89b-12d3-a456-426614174000',
      conteudo: { regra: 'Regra para especialidade' },
    })
    expect(result.especialidade_id).toBe('123e4567-e89b-12d3-a456-426614174000')
  })

  it('deve aceitar expira_em opcional', () => {
    const result = criarDiretrizSchema.parse({
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
      expira_em: '2024-12-31T23:59:59Z',
    })
    expect(result.expira_em).toBe('2024-12-31T23:59:59Z')
  })

  it('deve rejeitar escopo hospital sem hospital_id', () => {
    expect(() =>
      criarDiretrizSchema.parse({
        tipo: 'margem_negociacao',
        escopo: 'hospital',
        conteudo: { valor_maximo: 3000 },
      })
    ).toThrow()
  })

  it('deve rejeitar escopo especialidade sem especialidade_id', () => {
    expect(() =>
      criarDiretrizSchema.parse({
        tipo: 'regra_especial',
        escopo: 'especialidade',
        conteudo: { regra: 'Teste' },
      })
    ).toThrow()
  })

  it('deve rejeitar margem_negociacao sem valor nem percentual', () => {
    expect(() =>
      criarDiretrizSchema.parse({
        tipo: 'margem_negociacao',
        escopo: 'global',
        conteudo: {},
      })
    ).toThrow()
  })

  it('deve rejeitar regra_especial sem regra', () => {
    expect(() =>
      criarDiretrizSchema.parse({
        tipo: 'regra_especial',
        escopo: 'global',
        conteudo: {},
      })
    ).toThrow()
  })

  it('deve rejeitar info_adicional sem info', () => {
    expect(() =>
      criarDiretrizSchema.parse({
        tipo: 'info_adicional',
        escopo: 'global',
        conteudo: {},
      })
    ).toThrow()
  })
})

// =============================================================================
// cancelarDiretrizSchema
// =============================================================================

describe('cancelarDiretrizSchema', () => {
  it('deve aceitar status cancelada', () => {
    const result = cancelarDiretrizSchema.parse({ status: 'cancelada' })
    expect(result.status).toBe('cancelada')
  })

  it('deve rejeitar outro status', () => {
    expect(() => cancelarDiretrizSchema.parse({ status: 'ativa' })).toThrow()
  })

  it('deve rejeitar objeto vazio', () => {
    expect(() => cancelarDiretrizSchema.parse({})).toThrow()
  })
})
