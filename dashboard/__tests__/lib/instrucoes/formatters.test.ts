/**
 * Testes para lib/instrucoes/formatters.ts
 */

import { describe, it, expect } from 'vitest'
import {
  formatRelativeDate,
  formatExpirationDate,
  formatVagaDate,
  isExpired,
  getTipoLabel,
  getEscopoIcon,
  getEscopoBaseLabel,
  getEscopoLabel,
  formatCurrency,
  getConteudoLabel,
  buildDiretrizesUrl,
  buildDiretrizUrl,
} from '@/lib/instrucoes/formatters'
import type { Diretriz } from '@/lib/instrucoes/types'

// =============================================================================
// formatRelativeDate
// =============================================================================

describe('formatRelativeDate', () => {
  it('deve formatar data relativa', () => {
    const oneDayAgo = new Date()
    oneDayAgo.setDate(oneDayAgo.getDate() - 1)
    const result = formatRelativeDate(oneDayAgo.toISOString())
    expect(result).toContain('dia')
  })

  it('deve retornar string original se data invalida', () => {
    const result = formatRelativeDate('invalid-date')
    expect(result).toBe('invalid-date')
  })
})

// =============================================================================
// formatExpirationDate
// =============================================================================

describe('formatExpirationDate', () => {
  it('deve formatar data de expiracao (dd/MM HH:mm)', () => {
    const result = formatExpirationDate('2024-06-15T14:30:00Z')
    expect(result).toMatch(/\d{2}\/\d{2} \d{2}:\d{2}/)
  })

  it('deve retornar string original se data invalida', () => {
    const result = formatExpirationDate('invalid')
    expect(result).toBe('invalid')
  })
})

// =============================================================================
// formatVagaDate
// =============================================================================

describe('formatVagaDate', () => {
  it('deve formatar data de vaga (dd/MM)', () => {
    const result = formatVagaDate('2024-06-15T10:00:00Z')
    expect(result).toMatch(/\d{2}\/\d{2}/)
  })

  it('deve retornar string original se data invalida', () => {
    const result = formatVagaDate('invalid')
    expect(result).toBe('invalid')
  })
})

// =============================================================================
// isExpired
// =============================================================================

describe('isExpired', () => {
  it('deve retornar true para data passada', () => {
    const pastDate = new Date()
    pastDate.setDate(pastDate.getDate() - 1)
    expect(isExpired(pastDate.toISOString())).toBe(true)
  })

  it('deve retornar false para data futura', () => {
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + 1)
    expect(isExpired(futureDate.toISOString())).toBe(false)
  })

  it('deve retornar false para data invalida', () => {
    expect(isExpired('invalid')).toBe(false)
  })
})

// =============================================================================
// getTipoLabel
// =============================================================================

describe('getTipoLabel', () => {
  it('deve retornar label para margem_negociacao', () => {
    expect(getTipoLabel('margem_negociacao')).toBe('Margem de Negociacao')
  })

  it('deve retornar label para regra_especial', () => {
    expect(getTipoLabel('regra_especial')).toBe('Regra Especial')
  })

  it('deve retornar label para info_adicional', () => {
    expect(getTipoLabel('info_adicional')).toBe('Info Adicional')
  })
})

// =============================================================================
// getEscopoIcon
// =============================================================================

describe('getEscopoIcon', () => {
  it('deve retornar icone para vaga', () => {
    const icon = getEscopoIcon('vaga')
    expect(icon).toBeDefined()
  })

  it('deve retornar icone para hospital', () => {
    const icon = getEscopoIcon('hospital')
    expect(icon).toBeDefined()
  })

  it('deve retornar icone para global', () => {
    const icon = getEscopoIcon('global')
    expect(icon).toBeDefined()
  })
})

// =============================================================================
// getEscopoBaseLabel
// =============================================================================

describe('getEscopoBaseLabel', () => {
  it('deve retornar label para vaga', () => {
    expect(getEscopoBaseLabel('vaga')).toBe('Vaga')
  })

  it('deve retornar label para medico', () => {
    expect(getEscopoBaseLabel('medico')).toBe('Medico')
  })

  it('deve retornar label para hospital', () => {
    expect(getEscopoBaseLabel('hospital')).toBe('Hospital')
  })

  it('deve retornar label para especialidade', () => {
    expect(getEscopoBaseLabel('especialidade')).toBe('Especialidade')
  })

  it('deve retornar label para global', () => {
    expect(getEscopoBaseLabel('global')).toBe('Todas as conversas')
  })
})

// =============================================================================
// getEscopoLabel
// =============================================================================

describe('getEscopoLabel', () => {
  const baseDiretriz: Diretriz = {
    id: '1',
    tipo: 'margem_negociacao',
    escopo: 'global',
    conteudo: { valor_maximo: 3000 },
    criado_por: 'admin@test.com',
    criado_em: '2024-01-15T10:00:00Z',
    status: 'ativa',
  }

  it('deve retornar "Todas as conversas" para escopo global', () => {
    expect(getEscopoLabel(baseDiretriz)).toBe('Todas as conversas')
  })

  it('deve retornar nome do hospital para escopo hospital', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      escopo: 'hospital',
      hospitais: { nome: 'Hospital Sao Luiz' },
    }
    expect(getEscopoLabel(diretriz)).toBe('Hospital Sao Luiz')
  })

  it('deve retornar "Hospital" se hospitais for null', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      escopo: 'hospital',
      hospitais: null,
    }
    expect(getEscopoLabel(diretriz)).toBe('Hospital')
  })

  it('deve retornar nome da especialidade para escopo especialidade', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      escopo: 'especialidade',
      especialidades: { nome: 'Cardiologia' },
    }
    expect(getEscopoLabel(diretriz)).toBe('Cardiologia')
  })

  it('deve retornar nome do medico para escopo medico', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      escopo: 'medico',
      clientes: { primeiro_nome: 'Joao', sobrenome: 'Silva', telefone: '11999999999' },
    }
    expect(getEscopoLabel(diretriz)).toBe('Joao Silva')
  })

  it('deve retornar "Vaga dd/MM" para escopo vaga com data', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      escopo: 'vaga',
      vagas: { data: '2024-06-15T10:00:00Z', hospital_id: '1' },
    }
    const result = getEscopoLabel(diretriz)
    expect(result).toMatch(/Vaga \d{2}\/\d{2}/)
  })
})

// =============================================================================
// formatCurrency
// =============================================================================

describe('formatCurrency', () => {
  it('deve formatar valor com separador de milhar', () => {
    expect(formatCurrency(3000)).toBe('3.000')
  })

  it('deve formatar valores grandes', () => {
    expect(formatCurrency(1000000)).toBe('1.000.000')
  })

  it('deve formatar valores pequenos', () => {
    expect(formatCurrency(100)).toBe('100')
  })
})

// =============================================================================
// getConteudoLabel
// =============================================================================

describe('getConteudoLabel', () => {
  const baseDiretriz: Diretriz = {
    id: '1',
    tipo: 'margem_negociacao',
    escopo: 'global',
    conteudo: {},
    criado_por: 'admin@test.com',
    criado_em: '2024-01-15T10:00:00Z',
    status: 'ativa',
  }

  it('deve formatar margem com valor_maximo', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      tipo: 'margem_negociacao',
      conteudo: { valor_maximo: 3000 },
    }
    expect(getConteudoLabel(diretriz)).toBe('Ate R$ 3.000')
  })

  it('deve formatar margem com percentual_maximo', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      tipo: 'margem_negociacao',
      conteudo: { percentual_maximo: 15 },
    }
    expect(getConteudoLabel(diretriz)).toBe('Ate 15% acima')
  })

  it('deve retornar regra para regra_especial', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      tipo: 'regra_especial',
      conteudo: { regra: 'Pode flexibilizar horario' },
    }
    expect(getConteudoLabel(diretriz)).toBe('Pode flexibilizar horario')
  })

  it('deve retornar info para info_adicional', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      tipo: 'info_adicional',
      conteudo: { info: 'Hospital prefere medicos com UTI' },
    }
    expect(getConteudoLabel(diretriz)).toBe('Hospital prefere medicos com UTI')
  })

  it('deve retornar JSON se conteudo nao corresponde ao tipo', () => {
    const diretriz: Diretriz = {
      ...baseDiretriz,
      tipo: 'margem_negociacao',
      conteudo: {},
    }
    const result = getConteudoLabel(diretriz)
    expect(result).toBe('{}')
  })
})

// =============================================================================
// buildDiretrizesUrl
// =============================================================================

describe('buildDiretrizesUrl', () => {
  it('deve construir URL com status', () => {
    const url = buildDiretrizesUrl('/api/diretrizes', 'ativa')
    expect(url).toBe('/api/diretrizes?status=ativa')
  })

  it('deve construir URL com multiplos status', () => {
    const url = buildDiretrizesUrl('/api/diretrizes', 'expirada,cancelada')
    expect(url).toContain('status=expirada%2Ccancelada')
  })
})

// =============================================================================
// buildDiretrizUrl
// =============================================================================

describe('buildDiretrizUrl', () => {
  it('deve construir URL com ID', () => {
    const url = buildDiretrizUrl('/api/diretrizes', '123')
    expect(url).toBe('/api/diretrizes/123')
  })

  it('deve construir URL com UUID', () => {
    const url = buildDiretrizUrl('/api/diretrizes', '123e4567-e89b-12d3-a456-426614174000')
    expect(url).toBe('/api/diretrizes/123e4567-e89b-12d3-a456-426614174000')
  })
})
