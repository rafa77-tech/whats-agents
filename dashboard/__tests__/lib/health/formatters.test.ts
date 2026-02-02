import { describe, it, expect } from 'vitest'
import {
  formatTempoMedio,
  getProgressColor,
  shouldShowRateLimitWarning,
  calculatePercentage,
  getHealthStatusColors,
  getHealthStatusLabel,
  getServiceStatusColors,
  getAlertSeverityColors,
  getAlertSeverityLabel,
  getCircuitStateColors,
  sortAlertsBySeverity,
  countAlertsBySeverity,
  calculateGaugeOffset,
  formatPlural,
  getHealthStatusFromScore,
  getServiceStatusFromScore,
} from '@/lib/health/formatters'
import type { HealthAlert, AlertSeverity } from '@/lib/health/types'

describe('formatTempoMedio', () => {
  it('returns dash for null', () => {
    expect(formatTempoMedio(null)).toBe('-')
  })

  it('returns dash for undefined', () => {
    expect(formatTempoMedio(undefined)).toBe('-')
  })

  it('formats milliseconds under 1 second', () => {
    expect(formatTempoMedio(150)).toBe('150ms')
    expect(formatTempoMedio(999)).toBe('999ms')
  })

  it('formats seconds under 1 minute', () => {
    expect(formatTempoMedio(1000)).toBe('1.0s')
    expect(formatTempoMedio(2500)).toBe('2.5s')
    expect(formatTempoMedio(59999)).toBe('60.0s')
  })

  it('formats minutes for longer durations', () => {
    expect(formatTempoMedio(60000)).toBe('1.0m')
    expect(formatTempoMedio(90000)).toBe('1.5m')
    expect(formatTempoMedio(120000)).toBe('2.0m')
  })
})

describe('getProgressColor', () => {
  it('returns green for low percentages', () => {
    expect(getProgressColor(0)).toBe('bg-status-success-solid')
    expect(getProgressColor(50)).toBe('bg-status-success-solid')
    expect(getProgressColor(69)).toBe('bg-status-success-solid')
  })

  it('returns yellow for warning percentages', () => {
    expect(getProgressColor(70)).toBe('bg-status-warning-solid')
    expect(getProgressColor(80)).toBe('bg-status-warning-solid')
    expect(getProgressColor(89)).toBe('bg-status-warning-solid')
  })

  it('returns red for danger percentages', () => {
    expect(getProgressColor(90)).toBe('bg-status-error-solid')
    expect(getProgressColor(95)).toBe('bg-status-error-solid')
    expect(getProgressColor(100)).toBe('bg-status-error-solid')
  })
})

describe('shouldShowRateLimitWarning', () => {
  it('returns false below 80%', () => {
    expect(shouldShowRateLimitWarning(0)).toBe(false)
    expect(shouldShowRateLimitWarning(50)).toBe(false)
    expect(shouldShowRateLimitWarning(79)).toBe(false)
  })

  it('returns true at 80% or above', () => {
    expect(shouldShowRateLimitWarning(80)).toBe(true)
    expect(shouldShowRateLimitWarning(90)).toBe(true)
    expect(shouldShowRateLimitWarning(100)).toBe(true)
  })
})

describe('calculatePercentage', () => {
  it('returns 0 for zero limit', () => {
    expect(calculatePercentage(10, 0)).toBe(0)
  })

  it('returns 0 for negative limit', () => {
    expect(calculatePercentage(10, -5)).toBe(0)
  })

  it('calculates correct percentage', () => {
    expect(calculatePercentage(5, 10)).toBe(50)
    expect(calculatePercentage(75, 100)).toBe(75)
    expect(calculatePercentage(10, 20)).toBe(50)
  })

  it('rounds to nearest integer', () => {
    expect(calculatePercentage(1, 3)).toBe(33)
    expect(calculatePercentage(2, 3)).toBe(67)
  })
})

describe('getHealthStatusColors', () => {
  it('returns green colors for healthy', () => {
    const colors = getHealthStatusColors('healthy')
    expect(colors.stroke).toBe('#22c55e')
    expect(colors.text).toContain('status-success')
  })

  it('returns yellow colors for degraded', () => {
    const colors = getHealthStatusColors('degraded')
    expect(colors.stroke).toBe('#eab308')
    expect(colors.text).toContain('status-warning')
  })

  it('returns red colors for critical', () => {
    const colors = getHealthStatusColors('critical')
    expect(colors.stroke).toBe('#ef4444')
    expect(colors.text).toContain('status-error')
  })
})

describe('getHealthStatusLabel', () => {
  it('returns correct labels', () => {
    expect(getHealthStatusLabel('healthy')).toBe('HEALTHY')
    expect(getHealthStatusLabel('degraded')).toBe('DEGRADED')
    expect(getHealthStatusLabel('critical')).toBe('CRITICAL')
  })

  it('returns uppercase string for unknown status', () => {
    expect(getHealthStatusLabel('unknown' as any)).toBe('UNKNOWN')
  })
})

describe('getHealthStatusColors', () => {
  it('returns default colors for unknown status', () => {
    const colors = getHealthStatusColors('unknown' as any)
    expect(colors.text).toContain('status-neutral')
    expect(colors.badge).toContain('status-neutral')
  })
})

describe('getServiceStatusColors', () => {
  it('returns colors for all statuses', () => {
    expect(getServiceStatusColors('ok').bg).toContain('status-success')
    expect(getServiceStatusColors('warn').bg).toContain('status-warning')
    expect(getServiceStatusColors('error').bg).toContain('status-error')
  })

  it('returns default colors for unknown status', () => {
    const colors = getServiceStatusColors('unknown' as any)
    expect(colors.bg).toContain('status-neutral')
    expect(colors.text).toContain('status-neutral')
  })
})

describe('getAlertSeverityColors', () => {
  it('returns colors for all severities', () => {
    expect(getAlertSeverityColors('critical').bg).toContain('status-error')
    expect(getAlertSeverityColors('warn').bg).toContain('status-warning')
    expect(getAlertSeverityColors('info').bg).toContain('status-info')
  })

  it('returns default colors for unknown severity', () => {
    const colors = getAlertSeverityColors('unknown' as any)
    expect(colors.bg).toContain('status-neutral')
    expect(colors.border).toContain('status-neutral')
  })
})

describe('getAlertSeverityLabel', () => {
  it('returns Portuguese labels', () => {
    expect(getAlertSeverityLabel('critical')).toBe('Critico')
    expect(getAlertSeverityLabel('warn')).toBe('Alerta')
    expect(getAlertSeverityLabel('info')).toBe('Info')
  })

  it('returns original string for unknown severity', () => {
    expect(getAlertSeverityLabel('unknown' as any)).toBe('unknown')
  })
})

describe('getCircuitStateColors', () => {
  it('returns colors for all states', () => {
    expect(getCircuitStateColors('CLOSED').indicator).toContain('status-success')
    expect(getCircuitStateColors('HALF_OPEN').indicator).toContain('status-warning')
    expect(getCircuitStateColors('OPEN').indicator).toContain('status-error')
  })

  it('returns default colors for unknown states', () => {
    const colors = getCircuitStateColors('UNKNOWN_STATE' as any)
    expect(colors.bg).toContain('status-neutral')
    expect(colors.border).toContain('status-neutral')
    expect(colors.indicator).toContain('status-neutral')
    expect(colors.badge).toContain('status-neutral')
  })
})

describe('sortAlertsBySeverity', () => {
  it('sorts critical first, then warn, then info', () => {
    const alerts: { severity: AlertSeverity }[] = [
      { severity: 'info' },
      { severity: 'critical' },
      { severity: 'warn' },
      { severity: 'info' },
      { severity: 'critical' },
    ]

    const sorted = sortAlertsBySeverity(alerts)

    expect(sorted[0]?.severity).toBe('critical')
    expect(sorted[1]?.severity).toBe('critical')
    expect(sorted[2]?.severity).toBe('warn')
    expect(sorted[3]?.severity).toBe('info')
    expect(sorted[4]?.severity).toBe('info')
  })

  it('returns empty array for empty input', () => {
    expect(sortAlertsBySeverity([])).toEqual([])
  })

  it('does not mutate original array', () => {
    const original: { severity: AlertSeverity }[] = [{ severity: 'info' }, { severity: 'critical' }]
    sortAlertsBySeverity(original)
    expect(original[0]?.severity).toBe('info')
  })
})

describe('countAlertsBySeverity', () => {
  it('counts alerts correctly', () => {
    const alerts: HealthAlert[] = [
      { id: '1', tipo: 'test', severity: 'critical', message: 'a', source: 'test' },
      { id: '2', tipo: 'test', severity: 'critical', message: 'b', source: 'test' },
      { id: '3', tipo: 'test', severity: 'warn', message: 'c', source: 'test' },
      { id: '4', tipo: 'test', severity: 'info', message: 'd', source: 'test' },
      { id: '5', tipo: 'test', severity: 'info', message: 'e', source: 'test' },
      { id: '6', tipo: 'test', severity: 'info', message: 'f', source: 'test' },
    ]

    const counts = countAlertsBySeverity(alerts)

    expect(counts.critical).toBe(2)
    expect(counts.warn).toBe(1)
    expect(counts.info).toBe(3)
  })

  it('returns zeros for empty array', () => {
    const counts = countAlertsBySeverity([])
    expect(counts.critical).toBe(0)
    expect(counts.warn).toBe(0)
    expect(counts.info).toBe(0)
  })
})

describe('calculateGaugeOffset', () => {
  it('returns full circumference for 0 score', () => {
    const result = calculateGaugeOffset(0)
    expect(result.strokeDashoffset).toBe(result.circumference)
  })

  it('returns 0 offset for 100 score', () => {
    const result = calculateGaugeOffset(100)
    expect(result.strokeDashoffset).toBeCloseTo(0, 5)
  })

  it('returns half offset for 50 score', () => {
    const result = calculateGaugeOffset(50)
    expect(result.strokeDashoffset).toBeCloseTo(result.circumference / 2, 5)
  })

  it('circumference is based on radius 45', () => {
    const result = calculateGaugeOffset(0)
    expect(result.circumference).toBeCloseTo(2 * Math.PI * 45, 5)
  })
})

describe('formatPlural', () => {
  it('returns singular for count 1', () => {
    expect(formatPlural(1, 'alerta')).toBe('alerta')
    expect(formatPlural(1, 'critico', 'criticos')).toBe('critico')
  })

  it('returns plural for count != 1', () => {
    expect(formatPlural(0, 'alerta')).toBe('alertas')
    expect(formatPlural(2, 'alerta')).toBe('alertas')
    expect(formatPlural(5, 'critico', 'criticos')).toBe('criticos')
  })

  it('adds s by default for plural', () => {
    expect(formatPlural(2, 'item')).toBe('items')
  })
})

describe('getHealthStatusFromScore', () => {
  it('returns healthy for score >= 80', () => {
    expect(getHealthStatusFromScore(80)).toBe('healthy')
    expect(getHealthStatusFromScore(90)).toBe('healthy')
    expect(getHealthStatusFromScore(100)).toBe('healthy')
  })

  it('returns degraded for score 50-79', () => {
    expect(getHealthStatusFromScore(50)).toBe('degraded')
    expect(getHealthStatusFromScore(65)).toBe('degraded')
    expect(getHealthStatusFromScore(79)).toBe('degraded')
  })

  it('returns critical for score < 50', () => {
    expect(getHealthStatusFromScore(0)).toBe('critical')
    expect(getHealthStatusFromScore(25)).toBe('critical')
    expect(getHealthStatusFromScore(49)).toBe('critical')
  })
})

describe('getServiceStatusFromScore', () => {
  it('returns ok for score >= 80', () => {
    expect(getServiceStatusFromScore(80)).toBe('ok')
    expect(getServiceStatusFromScore(100)).toBe('ok')
  })

  it('returns warn for score 51-79', () => {
    expect(getServiceStatusFromScore(51)).toBe('warn')
    expect(getServiceStatusFromScore(79)).toBe('warn')
  })

  it('returns error for score <= 50', () => {
    expect(getServiceStatusFromScore(0)).toBe('error')
    expect(getServiceStatusFromScore(50)).toBe('error')
  })
})
