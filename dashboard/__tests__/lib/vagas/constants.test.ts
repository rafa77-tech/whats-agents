import { describe, it, expect } from 'vitest'
import {
  STATUS_BADGE_COLORS,
  STATUS_INDICATOR_COLORS,
  STATUS_LABELS,
  STATUS_OPTIONS,
  ALL_STATUSES,
  WEEK_DAYS,
  PAGINATION,
} from '@/lib/vagas/constants'

describe('STATUS_BADGE_COLORS', () => {
  it('has colors for all statuses', () => {
    ALL_STATUSES.forEach((status) => {
      expect(STATUS_BADGE_COLORS[status]).toBeDefined()
      expect(STATUS_BADGE_COLORS[status]).toContain('bg-')
      expect(STATUS_BADGE_COLORS[status]).toContain('text-')
    })
  })

  it('has consistent format for all colors', () => {
    Object.values(STATUS_BADGE_COLORS).forEach((color) => {
      expect(color).toMatch(/^bg-\w+-\d+ text-\w+-\d+$/)
    })
  })
})

describe('STATUS_INDICATOR_COLORS', () => {
  it('has colors for all statuses', () => {
    ALL_STATUSES.forEach((status) => {
      expect(STATUS_INDICATOR_COLORS[status]).toBeDefined()
      expect(STATUS_INDICATOR_COLORS[status]).toContain('bg-')
    })
  })

  it('has consistent format for all colors', () => {
    Object.values(STATUS_INDICATOR_COLORS).forEach((color) => {
      expect(color).toMatch(/^bg-\w+-\d+$/)
    })
  })
})

describe('STATUS_LABELS', () => {
  it('has labels for all statuses', () => {
    ALL_STATUSES.forEach((status) => {
      expect(STATUS_LABELS[status]).toBeDefined()
      expect(STATUS_LABELS[status].length).toBeGreaterThan(0)
    })
  })

  it('labels are capitalized in Portuguese', () => {
    expect(STATUS_LABELS.aberta).toBe('Aberta')
    expect(STATUS_LABELS.reservada).toBe('Reservada')
    expect(STATUS_LABELS.confirmada).toBe('Confirmada')
    expect(STATUS_LABELS.cancelada).toBe('Cancelada')
    expect(STATUS_LABELS.realizada).toBe('Realizada')
    expect(STATUS_LABELS.fechada).toBe('Fechada')
  })
})

describe('STATUS_OPTIONS', () => {
  it('has value and label for each option', () => {
    STATUS_OPTIONS.forEach((option) => {
      expect(option.value).toBeDefined()
      expect(option.label).toBeDefined()
    })
  })

  it('values match status keys', () => {
    const values = STATUS_OPTIONS.map((opt) => opt.value)
    expect(values).toContain('aberta')
    expect(values).toContain('reservada')
    expect(values).toContain('confirmada')
    expect(values).toContain('cancelada')
    expect(values).toContain('realizada')
  })

  it('labels match STATUS_LABELS values', () => {
    STATUS_OPTIONS.forEach((option) => {
      expect(option.label).toBe(STATUS_LABELS[option.value as keyof typeof STATUS_LABELS])
    })
  })
})

describe('ALL_STATUSES', () => {
  it('contains all 6 statuses', () => {
    expect(ALL_STATUSES).toHaveLength(6)
  })

  it('contains expected statuses', () => {
    expect(ALL_STATUSES).toContain('aberta')
    expect(ALL_STATUSES).toContain('reservada')
    expect(ALL_STATUSES).toContain('confirmada')
    expect(ALL_STATUSES).toContain('cancelada')
    expect(ALL_STATUSES).toContain('realizada')
    expect(ALL_STATUSES).toContain('fechada')
  })
})

describe('WEEK_DAYS', () => {
  it('has 7 days', () => {
    expect(WEEK_DAYS).toHaveLength(7)
  })

  it('starts with Sunday (Portuguese convention for Brazil)', () => {
    expect(WEEK_DAYS[0]).toBe('Dom')
  })

  it('has correct Portuguese abbreviations', () => {
    expect(WEEK_DAYS).toEqual(['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'])
  })
})

describe('PAGINATION', () => {
  it('has default page size', () => {
    expect(PAGINATION.DEFAULT_PAGE_SIZE).toBe(20)
  })

  it('has calendar page size', () => {
    expect(PAGINATION.CALENDAR_PAGE_SIZE).toBe(500)
  })

  it('calendar page size is larger than default', () => {
    expect(PAGINATION.CALENDAR_PAGE_SIZE).toBeGreaterThan(PAGINATION.DEFAULT_PAGE_SIZE)
  })
})
