import { describe, it, expect } from 'vitest'
import {
  getInitials,
  getStageColor,
  getStageLabel,
  getEventColor,
  formatFullName,
  formatLocation,
} from '@/lib/medicos/formatters'

describe('getInitials', () => {
  it('returns initials from full name', () => {
    expect(getInitials('João Silva')).toBe('JS')
    expect(getInitials('Maria Santos')).toBe('MS')
  })

  it('handles single name', () => {
    expect(getInitials('João')).toBe('J')
  })

  it('takes only first two names', () => {
    expect(getInitials('João Carlos Silva')).toBe('JC')
    expect(getInitials('Ana Maria de Souza Santos')).toBe('AM')
  })

  it('returns uppercase initials', () => {
    expect(getInitials('joão silva')).toBe('JS')
  })

  it('returns XX for empty or null input', () => {
    expect(getInitials('')).toBe('XX')
    expect(getInitials(null)).toBe('XX')
    expect(getInitials(undefined)).toBe('XX')
  })

  it('handles whitespace-only input', () => {
    expect(getInitials('   ')).toBe('XX')
  })

  it('handles names with extra spaces', () => {
    expect(getInitials('  João   Silva  ')).toBe('JS')
  })
})

describe('getStageColor', () => {
  it('returns correct color for Portuguese stages', () => {
    expect(getStageColor('novo')).toBe('bg-status-neutral text-status-neutral-foreground')
    expect(getStageColor('respondeu')).toBe('bg-status-info text-status-info-foreground')
    expect(getStageColor('negociando')).toBe('bg-status-warning text-status-warning-foreground')
    expect(getStageColor('convertido')).toBe('bg-status-success text-status-success-foreground')
    expect(getStageColor('perdido')).toBe('bg-status-error text-status-error-foreground')
  })

  it('returns correct color for English stages', () => {
    expect(getStageColor('prospecting')).toBe('bg-status-neutral text-status-neutral-foreground')
    expect(getStageColor('engaged')).toBe('bg-status-info text-status-info-foreground')
    expect(getStageColor('negotiating')).toBe('bg-status-warning text-status-warning-foreground')
    expect(getStageColor('converted')).toBe('bg-status-success text-status-success-foreground')
    expect(getStageColor('lost')).toBe('bg-status-error text-status-error-foreground')
  })

  it('returns default color for unknown stage', () => {
    expect(getStageColor('unknown')).toBe('bg-status-neutral text-status-neutral-foreground')
    expect(getStageColor('')).toBe('bg-status-neutral text-status-neutral-foreground')
  })

  it('returns default color for null/undefined', () => {
    expect(getStageColor(null)).toBe('bg-status-neutral text-status-neutral-foreground')
    expect(getStageColor(undefined)).toBe('bg-status-neutral text-status-neutral-foreground')
  })
})

describe('getStageLabel', () => {
  it('returns correct label for Portuguese stages', () => {
    expect(getStageLabel('novo')).toBe('Novo')
    expect(getStageLabel('respondeu')).toBe('Respondeu')
    expect(getStageLabel('negociando')).toBe('Negociando')
    expect(getStageLabel('convertido')).toBe('Convertido')
    expect(getStageLabel('perdido')).toBe('Perdido')
  })

  it('returns correct label for English stages', () => {
    expect(getStageLabel('prospecting')).toBe('Prospecção')
    expect(getStageLabel('engaged')).toBe('Engajado')
    expect(getStageLabel('negotiating')).toBe('Negociando')
    expect(getStageLabel('converted')).toBe('Convertido')
    expect(getStageLabel('lost')).toBe('Perdido')
  })

  it('returns raw stage for unknown stage', () => {
    expect(getStageLabel('custom_stage')).toBe('custom_stage')
  })

  it('returns Desconhecido for null/undefined', () => {
    expect(getStageLabel(null)).toBe('Desconhecido')
    expect(getStageLabel(undefined)).toBe('Desconhecido')
  })
})

describe('getEventColor', () => {
  it('returns correct color for each event type', () => {
    expect(getEventColor('message_sent')).toBe('bg-status-info text-status-info-foreground')
    expect(getEventColor('message_received')).toBe('bg-status-success text-status-success-foreground')
    expect(getEventColor('handoff')).toBe('bg-status-warning text-status-warning-foreground')
  })

  it('returns default color for unknown event type', () => {
    expect(getEventColor('unknown')).toBe('bg-status-neutral text-status-neutral-foreground')
    expect(getEventColor('')).toBe('bg-status-neutral text-status-neutral-foreground')
  })
})

describe('formatFullName', () => {
  it('combines first and last name', () => {
    expect(formatFullName('João', 'Silva')).toBe('João Silva')
  })

  it('handles only first name', () => {
    expect(formatFullName('João', null)).toBe('João')
    expect(formatFullName('João', undefined)).toBe('João')
  })

  it('handles only last name', () => {
    expect(formatFullName(null, 'Silva')).toBe('Silva')
    expect(formatFullName(undefined, 'Silva')).toBe('Silva')
  })

  it('returns Sem nome for empty input', () => {
    expect(formatFullName(null, null)).toBe('Sem nome')
    expect(formatFullName(undefined, undefined)).toBe('Sem nome')
    expect(formatFullName('', '')).toBe('Sem nome')
  })
})

describe('formatLocation', () => {
  it('combines city and state', () => {
    expect(formatLocation('São Paulo', 'SP')).toBe('São Paulo, SP')
  })

  it('returns only city when no state', () => {
    expect(formatLocation('São Paulo', null)).toBe('São Paulo')
    expect(formatLocation('São Paulo', undefined)).toBe('São Paulo')
  })

  it('returns empty string when no city', () => {
    expect(formatLocation(null, 'SP')).toBe('')
    expect(formatLocation(undefined, 'SP')).toBe('')
    expect(formatLocation('', 'SP')).toBe('')
  })

  it('returns empty string for empty input', () => {
    expect(formatLocation(null, null)).toBe('')
    expect(formatLocation(undefined, undefined)).toBe('')
  })
})
