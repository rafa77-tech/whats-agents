import { describe, it, expect } from 'vitest'
import {
  LINK_STATUS_LABELS,
  LINK_STATUS_BADGE_COLORS,
  QUEUE_STATUS_LABELS,
  QUEUE_STATUS_BADGE_COLORS,
  DIAS_SEMANA,
  DEFAULT_CONFIG,
  CONFIG_LIMITS,
  QUEUE_REFRESH_INTERVAL,
  DEFAULT_LINKS_LIMIT,
  WHATSAPP_LINK_PREFIX,
  ACCEPTED_FILE_EXTENSIONS,
  CAPACITY_WARNING_THRESHOLD,
  CAPACITY_DANGER_THRESHOLD,
} from '@/lib/group-entry/constants'

describe('LINK_STATUS_LABELS', () => {
  it('has all required statuses', () => {
    expect(LINK_STATUS_LABELS).toHaveProperty('pending')
    expect(LINK_STATUS_LABELS).toHaveProperty('validated')
    expect(LINK_STATUS_LABELS).toHaveProperty('scheduled')
    expect(LINK_STATUS_LABELS).toHaveProperty('processed')
    expect(LINK_STATUS_LABELS).toHaveProperty('failed')
  })

  it('has non-empty labels', () => {
    Object.values(LINK_STATUS_LABELS).forEach((label) => {
      expect(label.length).toBeGreaterThan(0)
    })
  })
})

describe('LINK_STATUS_BADGE_COLORS', () => {
  it('has all required statuses', () => {
    expect(LINK_STATUS_BADGE_COLORS).toHaveProperty('pending')
    expect(LINK_STATUS_BADGE_COLORS).toHaveProperty('validated')
    expect(LINK_STATUS_BADGE_COLORS).toHaveProperty('scheduled')
    expect(LINK_STATUS_BADGE_COLORS).toHaveProperty('processed')
    expect(LINK_STATUS_BADGE_COLORS).toHaveProperty('failed')
  })

  it('has valid Tailwind classes', () => {
    Object.values(LINK_STATUS_BADGE_COLORS).forEach((color) => {
      expect(color).toMatch(/^bg-\w+-\d+ text-\w+-\d+$/)
    })
  })
})

describe('QUEUE_STATUS_LABELS', () => {
  it('has all required statuses', () => {
    expect(QUEUE_STATUS_LABELS).toHaveProperty('queued')
    expect(QUEUE_STATUS_LABELS).toHaveProperty('processing')
  })
})

describe('QUEUE_STATUS_BADGE_COLORS', () => {
  it('has all required statuses', () => {
    expect(QUEUE_STATUS_BADGE_COLORS).toHaveProperty('queued')
    expect(QUEUE_STATUS_BADGE_COLORS).toHaveProperty('processing')
  })
})

describe('DIAS_SEMANA', () => {
  it('has 7 days', () => {
    expect(DIAS_SEMANA).toHaveLength(7)
  })

  it('has correct keys', () => {
    const keys = DIAS_SEMANA.map((d) => d.key)
    expect(keys).toContain('seg')
    expect(keys).toContain('ter')
    expect(keys).toContain('qua')
    expect(keys).toContain('qui')
    expect(keys).toContain('sex')
    expect(keys).toContain('sab')
    expect(keys).toContain('dom')
  })

  it('starts with Monday', () => {
    const firstDay = DIAS_SEMANA[0]
    expect(firstDay).toBeDefined()
    expect(firstDay?.key).toBe('seg')
  })
})

describe('DEFAULT_CONFIG', () => {
  it('has all required fields', () => {
    expect(DEFAULT_CONFIG).toHaveProperty('gruposPorDia')
    expect(DEFAULT_CONFIG).toHaveProperty('intervaloMin')
    expect(DEFAULT_CONFIG).toHaveProperty('intervaloMax')
    expect(DEFAULT_CONFIG).toHaveProperty('horarioInicio')
    expect(DEFAULT_CONFIG).toHaveProperty('horarioFim')
    expect(DEFAULT_CONFIG).toHaveProperty('diasAtivos')
    expect(DEFAULT_CONFIG).toHaveProperty('autoValidar')
    expect(DEFAULT_CONFIG).toHaveProperty('autoAgendar')
    expect(DEFAULT_CONFIG).toHaveProperty('notificarFalhas')
  })

  it('has sensible defaults', () => {
    expect(DEFAULT_CONFIG.gruposPorDia).toBeGreaterThan(0)
    expect(DEFAULT_CONFIG.intervaloMin).toBeLessThan(DEFAULT_CONFIG.intervaloMax)
    expect(DEFAULT_CONFIG.diasAtivos.length).toBeGreaterThan(0)
  })
})

describe('CONFIG_LIMITS', () => {
  it('has valid ranges', () => {
    expect(CONFIG_LIMITS.gruposPorDia.min).toBeLessThan(CONFIG_LIMITS.gruposPorDia.max)
    expect(CONFIG_LIMITS.intervaloMin.min).toBeLessThan(CONFIG_LIMITS.intervaloMin.max)
    expect(CONFIG_LIMITS.intervaloMax.min).toBeLessThan(CONFIG_LIMITS.intervaloMax.max)
  })
})

describe('QUEUE_REFRESH_INTERVAL', () => {
  it('is a positive number in milliseconds', () => {
    expect(QUEUE_REFRESH_INTERVAL).toBeGreaterThan(0)
    expect(QUEUE_REFRESH_INTERVAL).toBe(30000) // 30 seconds
  })
})

describe('DEFAULT_LINKS_LIMIT', () => {
  it('is a positive number', () => {
    expect(DEFAULT_LINKS_LIMIT).toBeGreaterThan(0)
    expect(DEFAULT_LINKS_LIMIT).toBe(20)
  })
})

describe('WHATSAPP_LINK_PREFIX', () => {
  it('is correct WhatsApp URL prefix', () => {
    expect(WHATSAPP_LINK_PREFIX).toBe('https://chat.whatsapp.com/')
  })
})

describe('ACCEPTED_FILE_EXTENSIONS', () => {
  it('includes csv and xlsx', () => {
    expect(ACCEPTED_FILE_EXTENSIONS).toContain('.csv')
    expect(ACCEPTED_FILE_EXTENSIONS).toContain('.xlsx')
  })
})

describe('CAPACITY_THRESHOLDS', () => {
  it('warning is less than danger', () => {
    expect(CAPACITY_WARNING_THRESHOLD).toBeLessThan(CAPACITY_DANGER_THRESHOLD)
  })

  it('are valid percentages', () => {
    expect(CAPACITY_WARNING_THRESHOLD).toBeGreaterThanOrEqual(0)
    expect(CAPACITY_WARNING_THRESHOLD).toBeLessThanOrEqual(100)
    expect(CAPACITY_DANGER_THRESHOLD).toBeGreaterThanOrEqual(0)
    expect(CAPACITY_DANGER_THRESHOLD).toBeLessThanOrEqual(100)
  })
})
