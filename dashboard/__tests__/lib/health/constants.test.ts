import { describe, it, expect } from 'vitest'
import {
  HEALTH_STATUS_COLORS,
  HEALTH_STATUS_LABELS,
  SERVICE_STATUS_COLORS,
  ALERT_SEVERITY_COLORS,
  ALERT_SEVERITY_LABELS,
  ALERT_SEVERITY_ORDER,
  CIRCUIT_STATE_COLORS,
  CIRCUIT_STATE_LEGEND,
  REFRESH_INTERVALS,
  DEFAULT_REFRESH_INTERVAL,
  DEFAULT_RATE_LIMIT,
  PROGRESS_THRESHOLDS,
  PROGRESS_COLORS,
  GAUGE_CONFIG,
  MAX_DISPLAYED_ALERTS,
  DEFAULT_SERVICES,
  DEFAULT_CIRCUITS,
} from '@/lib/health/constants'

describe('HEALTH_STATUS_COLORS', () => {
  it('has colors for all health statuses', () => {
    expect(HEALTH_STATUS_COLORS.healthy).toBeDefined()
    expect(HEALTH_STATUS_COLORS.degraded).toBeDefined()
    expect(HEALTH_STATUS_COLORS.critical).toBeDefined()
  })

  it('each status has all required color properties', () => {
    const requiredProps = ['stroke', 'bg', 'text', 'badge']

    Object.values(HEALTH_STATUS_COLORS).forEach((colors) => {
      requiredProps.forEach((prop) => {
        expect(colors).toHaveProperty(prop)
      })
    })
  })

  it('healthy uses success semantic colors', () => {
    expect(HEALTH_STATUS_COLORS.healthy.stroke).toContain('22c55e')
    expect(HEALTH_STATUS_COLORS.healthy.text).toContain('status-success')
  })

  it('degraded uses warning semantic colors', () => {
    expect(HEALTH_STATUS_COLORS.degraded.stroke).toContain('eab308')
    expect(HEALTH_STATUS_COLORS.degraded.text).toContain('status-warning')
  })

  it('critical uses error semantic colors', () => {
    expect(HEALTH_STATUS_COLORS.critical.stroke).toContain('ef4444')
    expect(HEALTH_STATUS_COLORS.critical.text).toContain('status-error')
  })
})

describe('HEALTH_STATUS_LABELS', () => {
  it('has labels for all statuses', () => {
    expect(HEALTH_STATUS_LABELS.healthy).toBe('HEALTHY')
    expect(HEALTH_STATUS_LABELS.degraded).toBe('DEGRADED')
    expect(HEALTH_STATUS_LABELS.critical).toBe('CRITICAL')
  })
})

describe('SERVICE_STATUS_COLORS', () => {
  it('has colors for all service statuses', () => {
    expect(SERVICE_STATUS_COLORS.ok).toBeDefined()
    expect(SERVICE_STATUS_COLORS.warn).toBeDefined()
    expect(SERVICE_STATUS_COLORS.error).toBeDefined()
  })

  it('each status has bg, text, and icon properties', () => {
    const requiredProps = ['bg', 'text', 'icon']

    Object.values(SERVICE_STATUS_COLORS).forEach((colors) => {
      requiredProps.forEach((prop) => {
        expect(colors).toHaveProperty(prop)
      })
    })
  })
})

describe('ALERT_SEVERITY_COLORS', () => {
  it('has colors for all severities', () => {
    expect(ALERT_SEVERITY_COLORS.critical).toBeDefined()
    expect(ALERT_SEVERITY_COLORS.warn).toBeDefined()
    expect(ALERT_SEVERITY_COLORS.info).toBeDefined()
  })

  it('each severity has all required properties', () => {
    const requiredProps = ['bg', 'border', 'text', 'badge', 'icon']

    Object.values(ALERT_SEVERITY_COLORS).forEach((colors) => {
      requiredProps.forEach((prop) => {
        expect(colors).toHaveProperty(prop)
      })
    })
  })
})

describe('ALERT_SEVERITY_LABELS', () => {
  it('has Portuguese labels for all severities', () => {
    expect(ALERT_SEVERITY_LABELS.critical).toBe('Critico')
    expect(ALERT_SEVERITY_LABELS.warn).toBe('Alerta')
    expect(ALERT_SEVERITY_LABELS.info).toBe('Info')
  })
})

describe('ALERT_SEVERITY_ORDER', () => {
  it('critical has highest priority (lowest number)', () => {
    expect(ALERT_SEVERITY_ORDER.critical).toBe(0)
  })

  it('warn has medium priority', () => {
    expect(ALERT_SEVERITY_ORDER.warn).toBe(1)
  })

  it('info has lowest priority (highest number)', () => {
    expect(ALERT_SEVERITY_ORDER.info).toBe(2)
  })

  it('maintains proper ordering', () => {
    expect(ALERT_SEVERITY_ORDER.critical).toBeLessThan(ALERT_SEVERITY_ORDER.warn)
    expect(ALERT_SEVERITY_ORDER.warn).toBeLessThan(ALERT_SEVERITY_ORDER.info)
  })
})

describe('CIRCUIT_STATE_COLORS', () => {
  it('has colors for all circuit states', () => {
    expect(CIRCUIT_STATE_COLORS.CLOSED).toBeDefined()
    expect(CIRCUIT_STATE_COLORS.HALF_OPEN).toBeDefined()
    expect(CIRCUIT_STATE_COLORS.OPEN).toBeDefined()
  })

  it('each state has all required properties', () => {
    const requiredProps = ['bg', 'border', 'indicator', 'badge']

    Object.values(CIRCUIT_STATE_COLORS).forEach((colors) => {
      requiredProps.forEach((prop) => {
        expect(colors).toHaveProperty(prop)
      })
    })
  })

  it('CLOSED uses success semantic colors', () => {
    expect(CIRCUIT_STATE_COLORS.CLOSED.indicator).toContain('status-success')
  })

  it('HALF_OPEN uses warning semantic colors', () => {
    expect(CIRCUIT_STATE_COLORS.HALF_OPEN.indicator).toContain('status-warning')
  })

  it('OPEN uses error semantic colors', () => {
    expect(CIRCUIT_STATE_COLORS.OPEN.indicator).toContain('status-error')
  })
})

describe('CIRCUIT_STATE_LEGEND', () => {
  it('contains all state descriptions', () => {
    expect(CIRCUIT_STATE_LEGEND).toContain('CLOSED')
    expect(CIRCUIT_STATE_LEGEND).toContain('HALF_OPEN')
    expect(CIRCUIT_STATE_LEGEND).toContain('OPEN')
    expect(CIRCUIT_STATE_LEGEND).toContain('operacional')
    expect(CIRCUIT_STATE_LEGEND).toContain('testando')
    expect(CIRCUIT_STATE_LEGEND).toContain('bloqueado')
  })
})

describe('REFRESH_INTERVALS', () => {
  it('has 4 interval options', () => {
    expect(REFRESH_INTERVALS).toHaveLength(4)
  })

  it('includes 15s, 30s, 60s, and Off options', () => {
    const labels = REFRESH_INTERVALS.map((i) => i.label)
    expect(labels).toContain('15s')
    expect(labels).toContain('30s')
    expect(labels).toContain('60s')
    expect(labels).toContain('Off')
  })

  it('Off option has value 0', () => {
    const offOption = REFRESH_INTERVALS.find((i) => i.label === 'Off')
    expect(offOption?.value).toBe(0)
  })

  it('all intervals have correct millisecond values', () => {
    const interval15s = REFRESH_INTERVALS.find((i) => i.label === '15s')
    const interval30s = REFRESH_INTERVALS.find((i) => i.label === '30s')
    const interval60s = REFRESH_INTERVALS.find((i) => i.label === '60s')

    expect(interval15s?.value).toBe(15000)
    expect(interval30s?.value).toBe(30000)
    expect(interval60s?.value).toBe(60000)
  })
})

describe('DEFAULT_REFRESH_INTERVAL', () => {
  it('is set to 30 seconds', () => {
    expect(DEFAULT_REFRESH_INTERVAL).toBe(30000)
  })
})

describe('DEFAULT_RATE_LIMIT', () => {
  it('has hourly limit of 20', () => {
    expect(DEFAULT_RATE_LIMIT.hourly.limit).toBe(20)
    expect(DEFAULT_RATE_LIMIT.hourly.used).toBe(0)
  })

  it('has daily limit of 100', () => {
    expect(DEFAULT_RATE_LIMIT.daily.limit).toBe(100)
    expect(DEFAULT_RATE_LIMIT.daily.used).toBe(0)
  })
})

describe('PROGRESS_THRESHOLDS', () => {
  it('has warning threshold at 70', () => {
    expect(PROGRESS_THRESHOLDS.WARNING).toBe(70)
  })

  it('has danger threshold at 90', () => {
    expect(PROGRESS_THRESHOLDS.DANGER).toBe(90)
  })

  it('has warning display threshold at 80', () => {
    expect(PROGRESS_THRESHOLDS.WARNING_DISPLAY).toBe(80)
  })

  it('thresholds are in correct order', () => {
    expect(PROGRESS_THRESHOLDS.WARNING).toBeLessThan(PROGRESS_THRESHOLDS.WARNING_DISPLAY)
    expect(PROGRESS_THRESHOLDS.WARNING_DISPLAY).toBeLessThan(PROGRESS_THRESHOLDS.DANGER)
  })
})

describe('PROGRESS_COLORS', () => {
  it('has semantic colors for all levels', () => {
    expect(PROGRESS_COLORS.SAFE).toContain('status-success')
    expect(PROGRESS_COLORS.WARNING).toContain('status-warning')
    expect(PROGRESS_COLORS.DANGER).toContain('status-error')
  })
})

describe('GAUGE_CONFIG', () => {
  it('has correct radius', () => {
    expect(GAUGE_CONFIG.RADIUS).toBe(45)
  })

  it('has correct stroke width', () => {
    expect(GAUGE_CONFIG.STROKE_WIDTH).toBe(8)
  })

  it('has background stroke color', () => {
    expect(GAUGE_CONFIG.BACKGROUND_STROKE).toBe('#e5e7eb')
  })

  it('has transition duration', () => {
    expect(GAUGE_CONFIG.TRANSITION_DURATION).toBe(500)
  })
})

describe('MAX_DISPLAYED_ALERTS', () => {
  it('is set to 5', () => {
    expect(MAX_DISPLAYED_ALERTS).toBe(5)
  })
})

describe('DEFAULT_SERVICES', () => {
  it('has 4 default services', () => {
    expect(DEFAULT_SERVICES).toHaveLength(4)
  })

  it('includes WhatsApp, Redis, Supabase, and LLM', () => {
    const names = DEFAULT_SERVICES.map((s) => s.name)
    expect(names).toContain('WhatsApp')
    expect(names).toContain('Redis')
    expect(names).toContain('Supabase')
    expect(names).toContain('LLM')
  })

  it('each service has name and status', () => {
    DEFAULT_SERVICES.forEach((service) => {
      expect(service).toHaveProperty('name')
      expect(service).toHaveProperty('status')
    })
  })
})

describe('DEFAULT_CIRCUITS', () => {
  it('has 3 default circuit breakers', () => {
    expect(DEFAULT_CIRCUITS).toHaveLength(3)
  })

  it('includes evolution, claude, and supabase', () => {
    const names = DEFAULT_CIRCUITS.map((c) => c.name)
    expect(names).toContain('evolution')
    expect(names).toContain('claude')
    expect(names).toContain('supabase')
  })

  it('all circuits start in CLOSED state', () => {
    DEFAULT_CIRCUITS.forEach((circuit) => {
      expect(circuit.state).toBe('CLOSED')
    })
  })

  it('all circuits have threshold of 5', () => {
    DEFAULT_CIRCUITS.forEach((circuit) => {
      expect(circuit.threshold).toBe(5)
    })
  })

  it('all circuits start with 0 failures', () => {
    DEFAULT_CIRCUITS.forEach((circuit) => {
      expect(circuit.failures).toBe(0)
    })
  })
})
