import { describe, it, expect } from 'vitest'
import {
  KPI_STATUS_COLORS,
  ANOMALY_SEVERITY_COLORS,
  ANOMALY_SEVERITY_LABELS,
  ANOMALY_SEVERITY_ORDER,
  ANOMALY_RESOLUTION_COLORS,
  ANOMALY_RESOLUTION_LABELS,
  HEALTH_SCORE_THRESHOLDS,
  CONVERSION_RATE_THRESHOLDS,
  TIME_TO_FILL_THRESHOLDS,
  PROGRESS_THRESHOLDS,
  PROGRESS_COLORS,
  HEALTH_SCORE_COMPONENTS,
  DEFAULT_KPIS,
  DEFAULT_ANOMALIAS_SUMMARY,
  ANOMALIAS_FETCH_LIMIT,
} from '@/lib/integridade'

describe('KPI_STATUS_COLORS', () => {
  it('has all statuses defined', () => {
    expect(KPI_STATUS_COLORS).toHaveProperty('good')
    expect(KPI_STATUS_COLORS).toHaveProperty('warn')
    expect(KPI_STATUS_COLORS).toHaveProperty('bad')
  })

  it('good status has green colors', () => {
    expect(KPI_STATUS_COLORS.good.border).toContain('green')
    expect(KPI_STATUS_COLORS.good.text).toContain('green')
    expect(KPI_STATUS_COLORS.good.bg).toContain('green')
  })

  it('warn status has yellow colors', () => {
    expect(KPI_STATUS_COLORS.warn.border).toContain('yellow')
    expect(KPI_STATUS_COLORS.warn.text).toContain('yellow')
    expect(KPI_STATUS_COLORS.warn.bg).toContain('yellow')
  })

  it('bad status has red colors', () => {
    expect(KPI_STATUS_COLORS.bad.border).toContain('red')
    expect(KPI_STATUS_COLORS.bad.text).toContain('red')
    expect(KPI_STATUS_COLORS.bad.bg).toContain('red')
  })

  it('all statuses have required properties', () => {
    const requiredProps = ['border', 'text', 'bg', 'icon']
    Object.values(KPI_STATUS_COLORS).forEach((colors) => {
      requiredProps.forEach((prop) => {
        expect(colors).toHaveProperty(prop)
      })
    })
  })
})

describe('ANOMALY_SEVERITY_COLORS', () => {
  it('has all severities defined', () => {
    expect(ANOMALY_SEVERITY_COLORS).toHaveProperty('high')
    expect(ANOMALY_SEVERITY_COLORS).toHaveProperty('medium')
    expect(ANOMALY_SEVERITY_COLORS).toHaveProperty('low')
  })

  it('high severity has red colors', () => {
    expect(ANOMALY_SEVERITY_COLORS.high.icon).toContain('red')
    expect(ANOMALY_SEVERITY_COLORS.high.badge).toContain('red')
  })

  it('medium severity has yellow colors', () => {
    expect(ANOMALY_SEVERITY_COLORS.medium.icon).toContain('yellow')
    expect(ANOMALY_SEVERITY_COLORS.medium.badge).toContain('yellow')
  })

  it('low severity has blue colors', () => {
    expect(ANOMALY_SEVERITY_COLORS.low.icon).toContain('blue')
    expect(ANOMALY_SEVERITY_COLORS.low.badge).toContain('blue')
  })

  it('all severities have required properties', () => {
    const requiredProps = ['bg', 'text', 'icon', 'badge']
    Object.values(ANOMALY_SEVERITY_COLORS).forEach((colors) => {
      requiredProps.forEach((prop) => {
        expect(colors).toHaveProperty(prop)
      })
    })
  })
})

describe('ANOMALY_SEVERITY_LABELS', () => {
  it('has Portuguese labels', () => {
    expect(ANOMALY_SEVERITY_LABELS.high).toBe('Alta')
    expect(ANOMALY_SEVERITY_LABELS.medium).toBe('Media')
    expect(ANOMALY_SEVERITY_LABELS.low).toBe('Baixa')
  })
})

describe('ANOMALY_SEVERITY_ORDER', () => {
  it('high has lowest order (highest priority)', () => {
    expect(ANOMALY_SEVERITY_ORDER.high).toBeLessThan(ANOMALY_SEVERITY_ORDER.medium)
    expect(ANOMALY_SEVERITY_ORDER.high).toBeLessThan(ANOMALY_SEVERITY_ORDER.low)
  })

  it('medium is between high and low', () => {
    expect(ANOMALY_SEVERITY_ORDER.medium).toBeGreaterThan(ANOMALY_SEVERITY_ORDER.high)
    expect(ANOMALY_SEVERITY_ORDER.medium).toBeLessThan(ANOMALY_SEVERITY_ORDER.low)
  })

  it('low has highest order (lowest priority)', () => {
    expect(ANOMALY_SEVERITY_ORDER.low).toBeGreaterThan(ANOMALY_SEVERITY_ORDER.high)
    expect(ANOMALY_SEVERITY_ORDER.low).toBeGreaterThan(ANOMALY_SEVERITY_ORDER.medium)
  })
})

describe('ANOMALY_RESOLUTION_COLORS', () => {
  it('resolvida has green colors', () => {
    expect(ANOMALY_RESOLUTION_COLORS.resolvida.bg).toContain('green')
    expect(ANOMALY_RESOLUTION_COLORS.resolvida.text).toContain('green')
  })

  it('aberta has yellow colors', () => {
    expect(ANOMALY_RESOLUTION_COLORS.aberta.bg).toContain('yellow')
    expect(ANOMALY_RESOLUTION_COLORS.aberta.text).toContain('yellow')
  })
})

describe('ANOMALY_RESOLUTION_LABELS', () => {
  it('has Portuguese labels', () => {
    expect(ANOMALY_RESOLUTION_LABELS.resolvida).toBe('Resolvida')
    expect(ANOMALY_RESOLUTION_LABELS.aberta).toBe('Aberta')
  })
})

describe('HEALTH_SCORE_THRESHOLDS', () => {
  it('has correct thresholds', () => {
    expect(HEALTH_SCORE_THRESHOLDS.GOOD).toBe(80)
    expect(HEALTH_SCORE_THRESHOLDS.WARN).toBe(60)
  })

  it('GOOD is greater than WARN', () => {
    expect(HEALTH_SCORE_THRESHOLDS.GOOD).toBeGreaterThan(HEALTH_SCORE_THRESHOLDS.WARN)
  })
})

describe('CONVERSION_RATE_THRESHOLDS', () => {
  it('has correct thresholds', () => {
    expect(CONVERSION_RATE_THRESHOLDS.GOOD).toBe(30)
    expect(CONVERSION_RATE_THRESHOLDS.WARN).toBe(20)
  })

  it('GOOD is greater than WARN', () => {
    expect(CONVERSION_RATE_THRESHOLDS.GOOD).toBeGreaterThan(CONVERSION_RATE_THRESHOLDS.WARN)
  })
})

describe('TIME_TO_FILL_THRESHOLDS', () => {
  it('has correct thresholds (lower is better)', () => {
    expect(TIME_TO_FILL_THRESHOLDS.GOOD).toBe(4)
    expect(TIME_TO_FILL_THRESHOLDS.WARN).toBe(8)
  })

  it('GOOD is less than WARN (lower is better)', () => {
    expect(TIME_TO_FILL_THRESHOLDS.GOOD).toBeLessThan(TIME_TO_FILL_THRESHOLDS.WARN)
  })
})

describe('PROGRESS_THRESHOLDS', () => {
  it('has correct thresholds', () => {
    expect(PROGRESS_THRESHOLDS.GOOD).toBe(80)
    expect(PROGRESS_THRESHOLDS.WARN).toBe(60)
  })
})

describe('PROGRESS_COLORS', () => {
  it('has correct color classes', () => {
    expect(PROGRESS_COLORS.GOOD).toContain('green')
    expect(PROGRESS_COLORS.WARN).toContain('yellow')
    expect(PROGRESS_COLORS.BAD).toContain('red')
  })
})

describe('HEALTH_SCORE_COMPONENTS', () => {
  it('has 4 components', () => {
    expect(HEALTH_SCORE_COMPONENTS).toHaveLength(4)
  })

  it('has all required components', () => {
    const keys = HEALTH_SCORE_COMPONENTS.map((c) => c.key)
    expect(keys).toContain('pressao')
    expect(keys).toContain('friccao')
    expect(keys).toContain('qualidade')
    expect(keys).toContain('spam')
  })

  it('all components have label and key', () => {
    HEALTH_SCORE_COMPONENTS.forEach((component) => {
      expect(component).toHaveProperty('label')
      expect(component).toHaveProperty('key')
      expect(component.label).toBeTruthy()
      expect(component.key).toBeTruthy()
    })
  })
})

describe('DEFAULT_KPIS', () => {
  it('has zero values for scores', () => {
    expect(DEFAULT_KPIS.healthScore).toBe(0)
    expect(DEFAULT_KPIS.conversionRate).toBe(0)
    expect(DEFAULT_KPIS.timeToFill).toBe(0)
  })

  it('has zero values for component scores', () => {
    expect(DEFAULT_KPIS.componentScores.pressao).toBe(0)
    expect(DEFAULT_KPIS.componentScores.friccao).toBe(0)
    expect(DEFAULT_KPIS.componentScores.qualidade).toBe(0)
    expect(DEFAULT_KPIS.componentScores.spam).toBe(0)
  })

  it('has empty recommendations array', () => {
    expect(DEFAULT_KPIS.recommendations).toEqual([])
  })
})

describe('DEFAULT_ANOMALIAS_SUMMARY', () => {
  it('has zero values', () => {
    expect(DEFAULT_ANOMALIAS_SUMMARY.abertas).toBe(0)
    expect(DEFAULT_ANOMALIAS_SUMMARY.resolvidas).toBe(0)
    expect(DEFAULT_ANOMALIAS_SUMMARY.total).toBe(0)
  })
})

describe('ANOMALIAS_FETCH_LIMIT', () => {
  it('is a positive number', () => {
    expect(ANOMALIAS_FETCH_LIMIT).toBeGreaterThan(0)
  })

  it('is 20', () => {
    expect(ANOMALIAS_FETCH_LIMIT).toBe(20)
  })
})
