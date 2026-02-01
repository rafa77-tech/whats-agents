/**
 * Testes para lib/qualidade/formatters.ts
 */

import { describe, it, expect } from 'vitest'
import {
  parseMetricsResponse,
  parseConversationsResponse,
  parseConversationDetailResponse,
  parseSuggestionsResponse,
  formatDateBR,
  formatTimeBR,
  formatDateTimeBR,
  formatShortId,
  isRatingsComplete,
  canCreateSuggestion,
  buildConversationsUrl,
  buildSuggestionsUrl,
  calculateFailureRate,
  calculateAverageRating,
} from '@/lib/qualidade/formatters'

// =============================================================================
// parseMetricsResponse
// =============================================================================

describe('parseMetricsResponse', () => {
  it('deve retornar metricas default quando ambos dados sao null', () => {
    const result = parseMetricsResponse(null, null)

    expect(result).toEqual({
      avaliadas: 0,
      pendentes: 0,
      scoreMedio: 0,
      validacaoTaxa: 98,
      validacaoFalhas: 0,
      padroesViolados: [],
    })
  })

  it('deve parsear dados de performance corretamente', () => {
    const performanceData = {
      avaliadas: 10,
      pendentes: 5,
      score_medio: 4.5,
    }

    const result = parseMetricsResponse(performanceData, null)

    expect(result.avaliadas).toBe(10)
    expect(result.pendentes).toBe(5)
    expect(result.scoreMedio).toBe(4.5)
  })

  it('deve parsear dados de validacao corretamente', () => {
    const validacaoData = {
      taxa_sucesso: 95,
      falhas: 5,
      padroes_violados: [{ padrao: 'emoji_excessivo', count: 3 }],
    }

    const result = parseMetricsResponse(null, validacaoData)

    expect(result.validacaoTaxa).toBe(95)
    expect(result.validacaoFalhas).toBe(5)
    expect(result.padroesViolados).toHaveLength(1)
    expect(result.padroesViolados[0]!.padrao).toBe('emoji_excessivo')
  })

  it('deve combinar dados de performance e validacao', () => {
    const performanceData = { avaliadas: 20, pendentes: 3, score_medio: 4.2 }
    const validacaoData = { taxa_sucesso: 99, falhas: 1, padroes_violados: [] }

    const result = parseMetricsResponse(performanceData, validacaoData)

    expect(result.avaliadas).toBe(20)
    expect(result.validacaoTaxa).toBe(99)
  })
})

// =============================================================================
// parseConversationsResponse
// =============================================================================

describe('parseConversationsResponse', () => {
  it('deve retornar array vazio quando conversas e undefined', () => {
    const result = parseConversationsResponse({})

    expect(result).toEqual([])
  })

  it('deve parsear lista de conversas corretamente', () => {
    const data = {
      conversas: [
        {
          id: 'abc123',
          medico_nome: 'Dr. Silva',
          total_mensagens: 15,
          status: 'ativa',
          avaliada: false,
          criada_em: '2024-01-15T10:00:00Z',
        },
        {
          id: 'def456',
          medico_nome: null,
          total_mensagens: null,
          status: 'finalizada',
          avaliada: true,
          criada_em: '2024-01-14T08:00:00Z',
        },
      ],
    }

    const result = parseConversationsResponse(data)

    expect(result).toHaveLength(2)
    expect(result[0]!).toEqual({
      id: 'abc123',
      medicoNome: 'Dr. Silva',
      mensagens: 15,
      status: 'ativa',
      avaliada: false,
      criadaEm: '2024-01-15T10:00:00Z',
    })
    expect(result[1]!.medicoNome).toBe('Desconhecido')
    expect(result[1]!.mensagens).toBe(0)
  })
})

// =============================================================================
// parseConversationDetailResponse
// =============================================================================

describe('parseConversationDetailResponse', () => {
  it('deve parsear detalhes de conversa corretamente', () => {
    const data = {
      id: 'conv123',
      medico_nome: 'Dr. Carlos',
      interacoes: [
        {
          id: 'msg1',
          remetente: 'julia' as const,
          conteudo: 'Oi, tudo bem?',
          criada_em: '2024-01-15T10:00:00Z',
        },
        {
          id: 'msg2',
          remetente: 'medico' as const,
          conteudo: 'Tudo sim!',
          criada_em: '2024-01-15T10:01:00Z',
        },
      ],
    }

    const result = parseConversationDetailResponse(data)

    expect(result.id).toBe('conv123')
    expect(result.medicoNome).toBe('Dr. Carlos')
    expect(result.mensagens).toHaveLength(2)
    expect(result.mensagens[0]!.remetente).toBe('julia')
    expect(result.mensagens[1]!.conteudo).toBe('Tudo sim!')
  })

  it('deve usar valor default quando medico_nome e undefined', () => {
    const data = {
      id: 'conv123',
      interacoes: [],
    }

    const result = parseConversationDetailResponse(data)

    expect(result.medicoNome).toBe('Desconhecido')
    expect(result.mensagens).toEqual([])
  })
})

// =============================================================================
// parseSuggestionsResponse
// =============================================================================

describe('parseSuggestionsResponse', () => {
  it('deve retornar array vazio quando sugestoes e undefined', () => {
    const result = parseSuggestionsResponse({})

    expect(result).toEqual([])
  })

  it('deve parsear lista de sugestoes corretamente', () => {
    const data = {
      sugestoes: [
        {
          id: 'sug1',
          tipo: 'tom',
          descricao: 'Usar tom mais informal',
          status: 'pending',
          exemplos: 'Ex: oi, tudo bem?',
          criada_em: '2024-01-15T10:00:00Z',
        },
        {
          id: 'sug2',
          tipo: 'objecao',
          descricao: 'Tratar objecao de preco',
          status: 'approved',
          criada_em: '2024-01-14T08:00:00Z',
        },
      ],
    }

    const result = parseSuggestionsResponse(data)

    expect(result).toHaveLength(2)
    expect(result[0]!.tipo).toBe('tom')
    expect(result[0]!.exemplos).toBe('Ex: oi, tudo bem?')
    expect(result[1]!.status).toBe('approved')
    expect(result[1]!.exemplos).toBeUndefined()
  })
})

// =============================================================================
// Formatadores de data
// =============================================================================

describe('formatDateBR', () => {
  it('deve formatar data em formato brasileiro', () => {
    const result = formatDateBR('2024-01-15T10:00:00Z')

    // Formato esperado: DD/MM/YYYY (pode variar com timezone)
    expect(result).toMatch(/^\d{2}\/\d{2}\/\d{4}$/)
  })

  it('deve retornar string original em caso de erro', () => {
    const result = formatDateBR('invalid-date')

    expect(result).toBe('invalid-date')
  })
})

describe('formatTimeBR', () => {
  it('deve formatar hora em formato HH:MM', () => {
    const result = formatTimeBR('2024-01-15T10:30:00Z')

    expect(result).toMatch(/^\d{2}:\d{2}$/)
  })

  it('deve retornar string vazia em caso de erro', () => {
    const result = formatTimeBR('invalid-date')

    expect(result).toBe('')
  })
})

describe('formatDateTimeBR', () => {
  it('deve formatar data e hora', () => {
    const result = formatDateTimeBR('2024-01-15T10:30:00Z')

    // Formato esperado: DD/MM/YYYY, HH:MM ou DD/MM/YYYY HH:MM
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
    expect(result).toMatch(/\d{2}:\d{2}/)
  })
})

// =============================================================================
// formatShortId
// =============================================================================

describe('formatShortId', () => {
  it('deve truncar ID para 8 caracteres com prefixo #', () => {
    const result = formatShortId('abc123def456ghi789')

    expect(result).toBe('#abc123de')
  })

  it('deve funcionar com IDs curtos', () => {
    const result = formatShortId('abc')

    expect(result).toBe('#abc')
  })
})

// =============================================================================
// Validadores
// =============================================================================

describe('isRatingsComplete', () => {
  it('deve retornar true quando todos os ratings sao maiores que 0', () => {
    const ratings = { naturalidade: 4, persona: 5, objetivo: 3, satisfacao: 4 }

    expect(isRatingsComplete(ratings)).toBe(true)
  })

  it('deve retornar false quando algum rating e 0', () => {
    const ratings = { naturalidade: 4, persona: 0, objetivo: 3, satisfacao: 4 }

    expect(isRatingsComplete(ratings)).toBe(false)
  })

  it('deve retornar false quando todos os ratings sao 0', () => {
    const ratings = { naturalidade: 0, persona: 0, objetivo: 0, satisfacao: 0 }

    expect(isRatingsComplete(ratings)).toBe(false)
  })
})

describe('canCreateSuggestion', () => {
  it('deve retornar true quando tipo e descricao estao preenchidos', () => {
    expect(canCreateSuggestion('tom', 'Usar tom mais informal')).toBe(true)
  })

  it('deve retornar false quando tipo esta vazio', () => {
    expect(canCreateSuggestion('', 'Descricao valida')).toBe(false)
  })

  it('deve retornar false quando descricao esta vazia', () => {
    expect(canCreateSuggestion('tom', '')).toBe(false)
  })

  it('deve retornar false quando descricao tem apenas espacos', () => {
    expect(canCreateSuggestion('tom', '   ')).toBe(false)
  })
})

// =============================================================================
// Builders de URL
// =============================================================================

describe('buildConversationsUrl', () => {
  it('deve construir URL com filtro e limite', () => {
    const result = buildConversationsUrl('/api/conversas', 'false', 20)

    expect(result).toBe('/api/conversas?avaliada=false&limit=20')
  })

  it('deve omitir filtro quando e "all"', () => {
    const result = buildConversationsUrl('/api/conversas', 'all', 20)

    expect(result).toBe('/api/conversas?limit=20')
  })
})

describe('buildSuggestionsUrl', () => {
  it('deve construir URL com filtro de status', () => {
    const result = buildSuggestionsUrl('/api/sugestoes', 'pending')

    expect(result).toBe('/api/sugestoes?status=pending')
  })

  it('deve omitir filtro quando e "all"', () => {
    const result = buildSuggestionsUrl('/api/sugestoes', 'all')

    expect(result).toBe('/api/sugestoes?')
  })
})

// =============================================================================
// Calculadores
// =============================================================================

describe('calculateFailureRate', () => {
  it('deve calcular taxa de falha a partir da taxa de sucesso', () => {
    expect(calculateFailureRate(95)).toBe(5)
    expect(calculateFailureRate(100)).toBe(0)
    expect(calculateFailureRate(0)).toBe(100)
  })
})

describe('calculateAverageRating', () => {
  it('deve calcular media dos ratings', () => {
    const ratings = { naturalidade: 4, persona: 5, objetivo: 3, satisfacao: 4 }

    expect(calculateAverageRating(ratings)).toBe(4)
  })

  it('deve retornar 0 quando todos os ratings sao 0', () => {
    const ratings = { naturalidade: 0, persona: 0, objetivo: 0, satisfacao: 0 }

    expect(calculateAverageRating(ratings)).toBe(0)
  })
})
