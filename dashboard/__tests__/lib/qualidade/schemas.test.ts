/**
 * Testes para lib/qualidade/schemas.ts
 */

import { describe, it, expect } from 'vitest'
import {
  conversationsQuerySchema,
  suggestionsQuerySchema,
  createEvaluationSchema,
  createSuggestionSchema,
  updateSuggestionSchema,
  parseConversationsQuery,
  parseSuggestionsQuery,
  parseCreateEvaluationBody,
  parseCreateSuggestionBody,
  parseUpdateSuggestionBody,
} from '@/lib/qualidade/schemas'

// =============================================================================
// conversationsQuerySchema
// =============================================================================

describe('conversationsQuerySchema', () => {
  it('deve aceitar query vazia com defaults', () => {
    const result = conversationsQuerySchema.parse({})
    expect(result.limit).toBe(20)
    expect(result.avaliada).toBeUndefined()
  })

  it('deve aceitar avaliada=true', () => {
    const result = conversationsQuerySchema.parse({ avaliada: 'true' })
    expect(result.avaliada).toBe('true')
  })

  it('deve aceitar avaliada=false', () => {
    const result = conversationsQuerySchema.parse({ avaliada: 'false' })
    expect(result.avaliada).toBe('false')
  })

  it('deve aceitar limit custom', () => {
    const result = conversationsQuerySchema.parse({ limit: '50' })
    expect(result.limit).toBe(50)
  })

  it('deve rejeitar limit maior que 100', () => {
    expect(() => conversationsQuerySchema.parse({ limit: '150' })).toThrow()
  })

  it('deve rejeitar avaliada invalido', () => {
    expect(() => conversationsQuerySchema.parse({ avaliada: 'maybe' })).toThrow()
  })
})

// =============================================================================
// suggestionsQuerySchema
// =============================================================================

describe('suggestionsQuerySchema', () => {
  it('deve aceitar query vazia', () => {
    const result = suggestionsQuerySchema.parse({})
    expect(result.status).toBeUndefined()
  })

  it('deve aceitar status pending', () => {
    const result = suggestionsQuerySchema.parse({ status: 'pending' })
    expect(result.status).toBe('pending')
  })

  it('deve aceitar status approved', () => {
    const result = suggestionsQuerySchema.parse({ status: 'approved' })
    expect(result.status).toBe('approved')
  })

  it('deve aceitar status rejected', () => {
    const result = suggestionsQuerySchema.parse({ status: 'rejected' })
    expect(result.status).toBe('rejected')
  })

  it('deve aceitar status implemented', () => {
    const result = suggestionsQuerySchema.parse({ status: 'implemented' })
    expect(result.status).toBe('implemented')
  })

  it('deve rejeitar status invalido', () => {
    expect(() => suggestionsQuerySchema.parse({ status: 'unknown' })).toThrow()
  })
})

// =============================================================================
// createEvaluationSchema
// =============================================================================

describe('createEvaluationSchema', () => {
  const validBody = {
    conversa_id: '550e8400-e29b-41d4-a716-446655440000',
    naturalidade: 4,
    persona: 5,
    objetivo: 3,
    satisfacao: 4,
    observacoes: 'Boa conversa',
  }

  it('deve aceitar body valido', () => {
    const result = createEvaluationSchema.parse(validBody)
    expect(result.conversa_id).toBe(validBody.conversa_id)
    expect(result.naturalidade).toBe(4)
  })

  it('deve aceitar observacoes vazias', () => {
    const body = { ...validBody, observacoes: undefined }
    const result = createEvaluationSchema.parse(body)
    expect(result.observacoes).toBe('')
  })

  it('deve rejeitar conversa_id invalido', () => {
    const body = { ...validBody, conversa_id: 'not-a-uuid' }
    expect(() => createEvaluationSchema.parse(body)).toThrow('ID de conversa invalido')
  })

  it('deve rejeitar nota menor que 1', () => {
    const body = { ...validBody, naturalidade: 0 }
    expect(() => createEvaluationSchema.parse(body)).toThrow()
  })

  it('deve rejeitar nota maior que 5', () => {
    const body = { ...validBody, persona: 6 }
    expect(() => createEvaluationSchema.parse(body)).toThrow()
  })

  it('deve rejeitar notas faltando', () => {
    const body = {
      conversa_id: validBody.conversa_id,
      naturalidade: 4,
      // faltando persona, objetivo, satisfacao
    }
    expect(() => createEvaluationSchema.parse(body)).toThrow()
  })

  it('deve rejeitar observacoes muito longas', () => {
    const body = { ...validBody, observacoes: 'a'.repeat(2001) }
    expect(() => createEvaluationSchema.parse(body)).toThrow()
  })
})

// =============================================================================
// createSuggestionSchema
// =============================================================================

describe('createSuggestionSchema', () => {
  const validBody = {
    tipo: 'tom' as const,
    descricao: 'Usar tom mais informal nas respostas',
  }

  it('deve aceitar body valido', () => {
    const result = createSuggestionSchema.parse(validBody)
    expect(result.tipo).toBe('tom')
    expect(result.descricao).toBe(validBody.descricao)
  })

  it('deve aceitar todos os tipos validos', () => {
    const tipos = ['tom', 'resposta', 'abertura', 'objecao'] as const
    tipos.forEach((tipo) => {
      const result = createSuggestionSchema.parse({ ...validBody, tipo })
      expect(result.tipo).toBe(tipo)
    })
  })

  it('deve aceitar exemplos opcionais', () => {
    const body = { ...validBody, exemplos: 'Exemplo de implementacao' }
    const result = createSuggestionSchema.parse(body)
    expect(result.exemplos).toBe('Exemplo de implementacao')
  })

  it('deve rejeitar tipo invalido', () => {
    const body = { ...validBody, tipo: 'invalido' }
    expect(() => createSuggestionSchema.parse(body)).toThrow('Tipo de sugestao invalido')
  })

  it('deve rejeitar descricao curta', () => {
    const body = { ...validBody, descricao: 'curta' }
    expect(() => createSuggestionSchema.parse(body)).toThrow(
      'Descricao deve ter pelo menos 10 caracteres'
    )
  })

  it('deve rejeitar descricao muito longa', () => {
    const body = { ...validBody, descricao: 'a'.repeat(2001) }
    expect(() => createSuggestionSchema.parse(body)).toThrow()
  })
})

// =============================================================================
// updateSuggestionSchema
// =============================================================================

describe('updateSuggestionSchema', () => {
  it('deve aceitar status pending', () => {
    const result = updateSuggestionSchema.parse({ status: 'pending' })
    expect(result.status).toBe('pending')
  })

  it('deve aceitar status approved', () => {
    const result = updateSuggestionSchema.parse({ status: 'approved' })
    expect(result.status).toBe('approved')
  })

  it('deve aceitar status rejected', () => {
    const result = updateSuggestionSchema.parse({ status: 'rejected' })
    expect(result.status).toBe('rejected')
  })

  it('deve aceitar status implemented', () => {
    const result = updateSuggestionSchema.parse({ status: 'implemented' })
    expect(result.status).toBe('implemented')
  })

  it('deve rejeitar status invalido', () => {
    expect(() => updateSuggestionSchema.parse({ status: 'unknown' })).toThrow('Status invalido')
  })

  it('deve rejeitar body vazio', () => {
    expect(() => updateSuggestionSchema.parse({})).toThrow()
  })
})

// =============================================================================
// Helper Functions
// =============================================================================

describe('parseConversationsQuery', () => {
  it('deve parsear query vazia', () => {
    const searchParams = new URLSearchParams()
    const result = parseConversationsQuery(searchParams)
    expect(result.limit).toBe(20)
    expect(result.avaliada).toBeUndefined()
  })

  it('deve parsear com avaliada', () => {
    const searchParams = new URLSearchParams('avaliada=true&limit=50')
    const result = parseConversationsQuery(searchParams)
    expect(result.avaliada).toBe('true')
    expect(result.limit).toBe(50)
  })
})

describe('parseSuggestionsQuery', () => {
  it('deve parsear query vazia', () => {
    const searchParams = new URLSearchParams()
    const result = parseSuggestionsQuery(searchParams)
    expect(result.status).toBeUndefined()
  })

  it('deve parsear com status', () => {
    const searchParams = new URLSearchParams('status=approved')
    const result = parseSuggestionsQuery(searchParams)
    expect(result.status).toBe('approved')
  })
})

describe('parseCreateEvaluationBody', () => {
  it('deve parsear body valido', () => {
    const body = {
      conversa_id: '550e8400-e29b-41d4-a716-446655440000',
      naturalidade: 4,
      persona: 5,
      objetivo: 3,
      satisfacao: 4,
      observacoes: 'Teste',
    }
    const result = parseCreateEvaluationBody(body)
    expect(result.conversa_id).toBe(body.conversa_id)
  })

  it('deve rejeitar body invalido', () => {
    expect(() => parseCreateEvaluationBody({ invalid: 'body' })).toThrow()
  })
})

describe('parseCreateSuggestionBody', () => {
  it('deve parsear body valido', () => {
    const body = {
      tipo: 'tom',
      descricao: 'Usar tom mais informal',
    }
    const result = parseCreateSuggestionBody(body)
    expect(result.tipo).toBe('tom')
  })

  it('deve rejeitar body invalido', () => {
    expect(() => parseCreateSuggestionBody({ tipo: 'invalid' })).toThrow()
  })
})

describe('parseUpdateSuggestionBody', () => {
  it('deve parsear body valido', () => {
    const result = parseUpdateSuggestionBody({ status: 'approved' })
    expect(result.status).toBe('approved')
  })

  it('deve rejeitar body invalido', () => {
    expect(() => parseUpdateSuggestionBody({ status: 'invalid' })).toThrow()
  })
})
