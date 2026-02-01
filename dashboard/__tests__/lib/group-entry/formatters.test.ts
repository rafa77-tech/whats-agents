import { describe, it, expect } from 'vitest'
import {
  getLinkStatusLabel,
  getLinkStatusBadgeColor,
  getQueueStatusLabel,
  getQueueStatusBadgeColor,
  formatLinkUrl,
  formatDate,
  formatTime,
  calculateCapacityPercentage,
  getCapacityColor,
  isCapacityWarning,
  configApiToUI,
  configUIToApi,
  validateConfig,
  isValidFileExtension,
} from '@/lib/group-entry/formatters'
import type { GroupEntryConfig, GroupEntryConfigUI } from '@/lib/group-entry/types'

describe('getLinkStatusLabel', () => {
  it('returns correct label for each status', () => {
    expect(getLinkStatusLabel('pending')).toBe('Pendente')
    expect(getLinkStatusLabel('validated')).toBe('Validado')
    expect(getLinkStatusLabel('scheduled')).toBe('Agendado')
    expect(getLinkStatusLabel('processed')).toBe('Processado')
    expect(getLinkStatusLabel('failed')).toBe('Falhou')
  })

  it('returns raw status for unknown status', () => {
    expect(getLinkStatusLabel('unknown')).toBe('unknown')
    expect(getLinkStatusLabel('')).toBe('')
  })
})

describe('getLinkStatusBadgeColor', () => {
  it('returns correct color for each status', () => {
    expect(getLinkStatusBadgeColor('pending')).toBe('bg-gray-100 text-gray-800')
    expect(getLinkStatusBadgeColor('validated')).toBe('bg-blue-100 text-blue-800')
    expect(getLinkStatusBadgeColor('scheduled')).toBe('bg-yellow-100 text-yellow-800')
    expect(getLinkStatusBadgeColor('processed')).toBe('bg-green-100 text-green-800')
    expect(getLinkStatusBadgeColor('failed')).toBe('bg-red-100 text-red-800')
  })

  it('returns default color for unknown status', () => {
    expect(getLinkStatusBadgeColor('unknown')).toBe('bg-gray-100 text-gray-800')
    expect(getLinkStatusBadgeColor('')).toBe('bg-gray-100 text-gray-800')
  })
})

describe('getQueueStatusLabel', () => {
  it('returns correct label for each status', () => {
    expect(getQueueStatusLabel('queued')).toBe('Na Fila')
    expect(getQueueStatusLabel('processing')).toBe('Processando')
  })

  it('returns raw status for unknown status', () => {
    expect(getQueueStatusLabel('unknown')).toBe('unknown')
  })
})

describe('getQueueStatusBadgeColor', () => {
  it('returns correct color for each status', () => {
    expect(getQueueStatusBadgeColor('queued')).toBe('bg-yellow-100 text-yellow-800')
    expect(getQueueStatusBadgeColor('processing')).toBe('bg-blue-100 text-blue-800')
  })

  it('returns default color for unknown status', () => {
    expect(getQueueStatusBadgeColor('unknown')).toBe('bg-gray-100 text-gray-800')
  })
})

describe('formatLinkUrl', () => {
  it('truncates WhatsApp link prefix', () => {
    expect(formatLinkUrl('https://chat.whatsapp.com/ABC123')).toBe('...ABC123')
    expect(formatLinkUrl('https://chat.whatsapp.com/xyz789')).toBe('...xyz789')
  })

  it('returns unchanged if not a WhatsApp link', () => {
    expect(formatLinkUrl('https://example.com/abc')).toBe('https://example.com/abc')
  })
})

describe('formatDate', () => {
  it('formats date in Brazilian format', () => {
    const result = formatDate('2026-01-15T10:00:00Z')
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
  })
})

describe('formatTime', () => {
  it('formats time with hours and minutes', () => {
    const result = formatTime('2026-01-15T14:30:00Z')
    expect(result).toMatch(/\d{2}:\d{2}/)
  })
})

describe('calculateCapacityPercentage', () => {
  it('calculates percentage correctly', () => {
    expect(calculateCapacityPercentage(50, 100)).toBe(50)
    expect(calculateCapacityPercentage(75, 100)).toBe(75)
    expect(calculateCapacityPercentage(100, 100)).toBe(100)
  })

  it('rounds to nearest integer', () => {
    expect(calculateCapacityPercentage(33, 100)).toBe(33)
    expect(calculateCapacityPercentage(1, 3)).toBe(33)
  })

  it('returns 0 for zero total', () => {
    expect(calculateCapacityPercentage(50, 0)).toBe(0)
    expect(calculateCapacityPercentage(0, 0)).toBe(0)
  })

  it('returns 0 for negative total', () => {
    expect(calculateCapacityPercentage(50, -10)).toBe(0)
  })
})

describe('getCapacityColor', () => {
  it('returns green for low usage', () => {
    expect(getCapacityColor(0)).toBe('bg-green-500')
    expect(getCapacityColor(50)).toBe('bg-green-500')
    expect(getCapacityColor(79)).toBe('bg-green-500')
  })

  it('returns yellow for warning level', () => {
    expect(getCapacityColor(80)).toBe('bg-yellow-500')
    expect(getCapacityColor(85)).toBe('bg-yellow-500')
    expect(getCapacityColor(89)).toBe('bg-yellow-500')
  })

  it('returns red for danger level', () => {
    expect(getCapacityColor(90)).toBe('bg-red-500')
    expect(getCapacityColor(95)).toBe('bg-red-500')
    expect(getCapacityColor(100)).toBe('bg-red-500')
  })
})

describe('isCapacityWarning', () => {
  it('returns false below threshold', () => {
    expect(isCapacityWarning(0)).toBe(false)
    expect(isCapacityWarning(50)).toBe(false)
    expect(isCapacityWarning(79)).toBe(false)
  })

  it('returns true at or above threshold', () => {
    expect(isCapacityWarning(80)).toBe(true)
    expect(isCapacityWarning(90)).toBe(true)
    expect(isCapacityWarning(100)).toBe(true)
  })
})

describe('configApiToUI', () => {
  it('converts snake_case to camelCase', () => {
    const apiConfig: GroupEntryConfig = {
      grupos_por_dia: 15,
      intervalo_min: 20,
      intervalo_max: 45,
      horario_inicio: '09:00',
      horario_fim: '18:00',
      dias_ativos: ['seg', 'ter', 'qua'],
      auto_validar: false,
      auto_agendar: true,
      notificar_falhas: false,
    }

    const result = configApiToUI(apiConfig)

    expect(result.gruposPorDia).toBe(15)
    expect(result.intervaloMin).toBe(20)
    expect(result.intervaloMax).toBe(45)
    expect(result.horarioInicio).toBe('09:00')
    expect(result.horarioFim).toBe('18:00')
    expect(result.diasAtivos).toEqual(['seg', 'ter', 'qua'])
    expect(result.autoValidar).toBe(false)
    expect(result.autoAgendar).toBe(true)
    expect(result.notificarFalhas).toBe(false)
  })

  it('uses defaults for missing values', () => {
    const result = configApiToUI({})

    expect(result.gruposPorDia).toBe(10)
    expect(result.intervaloMin).toBe(30)
    expect(result.intervaloMax).toBe(60)
    expect(result.horarioInicio).toBe('08:00')
    expect(result.horarioFim).toBe('20:00')
    expect(result.diasAtivos).toEqual(['seg', 'ter', 'qua', 'qui', 'sex'])
    expect(result.autoValidar).toBe(true)
    expect(result.autoAgendar).toBe(false)
    expect(result.notificarFalhas).toBe(true)
  })
})

describe('configUIToApi', () => {
  it('converts camelCase to snake_case', () => {
    const uiConfig: GroupEntryConfigUI = {
      gruposPorDia: 12,
      intervaloMin: 25,
      intervaloMax: 50,
      horarioInicio: '10:00',
      horarioFim: '19:00',
      diasAtivos: ['seg', 'qua', 'sex'],
      autoValidar: true,
      autoAgendar: false,
      notificarFalhas: true,
    }

    const result = configUIToApi(uiConfig)

    expect(result.grupos_por_dia).toBe(12)
    expect(result.intervalo_min).toBe(25)
    expect(result.intervalo_max).toBe(50)
    expect(result.horario_inicio).toBe('10:00')
    expect(result.horario_fim).toBe('19:00')
    expect(result.dias_ativos).toEqual(['seg', 'qua', 'sex'])
    expect(result.auto_validar).toBe(true)
    expect(result.auto_agendar).toBe(false)
    expect(result.notificar_falhas).toBe(true)
  })
})

describe('validateConfig', () => {
  const validConfig: GroupEntryConfigUI = {
    gruposPorDia: 10,
    intervaloMin: 30,
    intervaloMax: 60,
    horarioInicio: '08:00',
    horarioFim: '20:00',
    diasAtivos: ['seg', 'ter', 'qua', 'qui', 'sex'],
    autoValidar: true,
    autoAgendar: false,
    notificarFalhas: true,
  }

  it('returns empty array for valid config', () => {
    expect(validateConfig(validConfig)).toEqual([])
  })

  it('returns error when intervaloMin >= intervaloMax', () => {
    const config = { ...validConfig, intervaloMin: 60, intervaloMax: 30 }
    const errors = validateConfig(config)
    expect(errors).toContain('Intervalo mínimo deve ser menor que o máximo')
  })

  it('returns error when intervaloMin equals intervaloMax', () => {
    const config = { ...validConfig, intervaloMin: 30, intervaloMax: 30 }
    const errors = validateConfig(config)
    expect(errors).toContain('Intervalo mínimo deve ser menor que o máximo')
  })

  it('returns error when horarioInicio >= horarioFim', () => {
    const config = { ...validConfig, horarioInicio: '20:00', horarioFim: '08:00' }
    const errors = validateConfig(config)
    expect(errors).toContain('Horário de início deve ser anterior ao fim')
  })

  it('returns error when diasAtivos is empty', () => {
    const config = { ...validConfig, diasAtivos: [] }
    const errors = validateConfig(config)
    expect(errors).toContain('Selecione pelo menos um dia da semana')
  })

  it('returns error when gruposPorDia is out of range', () => {
    const configLow = { ...validConfig, gruposPorDia: 0 }
    const configHigh = { ...validConfig, gruposPorDia: 25 }

    expect(validateConfig(configLow)).toContain('Grupos por dia deve estar entre 1 e 20')
    expect(validateConfig(configHigh)).toContain('Grupos por dia deve estar entre 1 e 20')
  })

  it('returns multiple errors when multiple validations fail', () => {
    const config = {
      ...validConfig,
      intervaloMin: 60,
      intervaloMax: 30,
      diasAtivos: [],
      gruposPorDia: 0,
    }
    const errors = validateConfig(config)
    expect(errors.length).toBe(3)
  })
})

describe('isValidFileExtension', () => {
  it('returns true for valid extensions', () => {
    expect(isValidFileExtension('links.csv')).toBe(true)
    expect(isValidFileExtension('links.xlsx')).toBe(true)
    expect(isValidFileExtension('LINKS.CSV')).toBe(true)
    expect(isValidFileExtension('LINKS.XLSX')).toBe(true)
  })

  it('returns false for invalid extensions', () => {
    expect(isValidFileExtension('links.txt')).toBe(false)
    expect(isValidFileExtension('links.json')).toBe(false)
    expect(isValidFileExtension('links.xls')).toBe(false)
    expect(isValidFileExtension('links')).toBe(false)
  })
})
