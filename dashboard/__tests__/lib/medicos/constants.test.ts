import { describe, it, expect } from 'vitest'
import {
  STAGE_COLORS,
  STAGE_LABELS,
  STAGE_OPTIONS,
  ESPECIALIDADE_OPTIONS,
  EVENT_COLORS,
  ALL_STAGES,
  PAGINATION,
  SEARCH_DEBOUNCE_MS,
} from '@/lib/medicos/constants'

describe('STAGE_COLORS', () => {
  it('has colors for all Portuguese stages', () => {
    ALL_STAGES.forEach((stage) => {
      expect(STAGE_COLORS[stage]).toBeDefined()
      expect(STAGE_COLORS[stage]).toContain('bg-')
      expect(STAGE_COLORS[stage]).toContain('text-')
    })
  })

  it('has colors for English aliases', () => {
    const englishStages = ['prospecting', 'engaged', 'negotiating', 'converted', 'lost']
    englishStages.forEach((stage) => {
      expect(STAGE_COLORS[stage]).toBeDefined()
    })
  })

  it('has consistent format for all colors', () => {
    Object.values(STAGE_COLORS).forEach((color) => {
      expect(color).toMatch(/^bg-\w+-\d+ text-\w+-\d+$/)
    })
  })
})

describe('STAGE_LABELS', () => {
  it('has labels for all Portuguese stages', () => {
    ALL_STAGES.forEach((stage) => {
      const label = STAGE_LABELS[stage]
      expect(label).toBeDefined()
      expect(label?.length).toBeGreaterThan(0)
    })
  })

  it('has labels for English aliases', () => {
    const englishStages = ['prospecting', 'engaged', 'negotiating', 'converted', 'lost']
    englishStages.forEach((stage) => {
      expect(STAGE_LABELS[stage]).toBeDefined()
    })
  })

  it('labels are capitalized', () => {
    expect(STAGE_LABELS.novo).toBe('Novo')
    expect(STAGE_LABELS.respondeu).toBe('Respondeu')
    expect(STAGE_LABELS.negociando).toBe('Negociando')
    expect(STAGE_LABELS.convertido).toBe('Convertido')
    expect(STAGE_LABELS.perdido).toBe('Perdido')
  })
})

describe('STAGE_OPTIONS', () => {
  it('has 5 stage options', () => {
    expect(STAGE_OPTIONS).toHaveLength(5)
  })

  it('has value and label for each option', () => {
    STAGE_OPTIONS.forEach((option) => {
      expect(option.value).toBeDefined()
      expect(option.label).toBeDefined()
    })
  })

  it('values match stage keys', () => {
    const values = STAGE_OPTIONS.map((opt) => opt.value)
    expect(values).toContain('novo')
    expect(values).toContain('respondeu')
    expect(values).toContain('negociando')
    expect(values).toContain('convertido')
    expect(values).toContain('perdido')
  })

  it('labels match STAGE_LABELS values', () => {
    STAGE_OPTIONS.forEach((option) => {
      expect(option.label).toBe(STAGE_LABELS[option.value])
    })
  })
})

describe('ESPECIALIDADE_OPTIONS', () => {
  it('has 6 specialty options', () => {
    expect(ESPECIALIDADE_OPTIONS).toHaveLength(6)
  })

  it('has value and label for each option', () => {
    ESPECIALIDADE_OPTIONS.forEach((option) => {
      expect(option.value).toBeDefined()
      expect(option.label).toBeDefined()
    })
  })

  it('includes common specialties', () => {
    const values = ESPECIALIDADE_OPTIONS.map((opt) => opt.value)
    expect(values).toContain('Cardiologia')
    expect(values).toContain('Ortopedia')
    expect(values).toContain('Pediatria')
  })
})

describe('EVENT_COLORS', () => {
  it('has colors for all event types', () => {
    expect(EVENT_COLORS.message_sent).toBeDefined()
    expect(EVENT_COLORS.message_received).toBeDefined()
    expect(EVENT_COLORS.handoff).toBeDefined()
  })

  it('has consistent format for all colors', () => {
    Object.values(EVENT_COLORS).forEach((color) => {
      expect(color).toMatch(/^bg-\w+-\d+ text-\w+-\d+$/)
    })
  })

  it('uses distinct colors for each type', () => {
    expect(EVENT_COLORS.message_sent).not.toBe(EVENT_COLORS.message_received)
    expect(EVENT_COLORS.message_received).not.toBe(EVENT_COLORS.handoff)
    expect(EVENT_COLORS.handoff).not.toBe(EVENT_COLORS.message_sent)
  })
})

describe('ALL_STAGES', () => {
  it('contains 5 stages', () => {
    expect(ALL_STAGES).toHaveLength(5)
  })

  it('contains expected stages', () => {
    expect(ALL_STAGES).toContain('novo')
    expect(ALL_STAGES).toContain('respondeu')
    expect(ALL_STAGES).toContain('negociando')
    expect(ALL_STAGES).toContain('convertido')
    expect(ALL_STAGES).toContain('perdido')
  })
})

describe('PAGINATION', () => {
  it('has default page size', () => {
    expect(PAGINATION.DEFAULT_PAGE_SIZE).toBe(20)
  })
})

describe('SEARCH_DEBOUNCE_MS', () => {
  it('is set to 300ms', () => {
    expect(SEARCH_DEBOUNCE_MS).toBe(300)
  })
})
