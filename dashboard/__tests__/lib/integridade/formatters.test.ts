import { describe, it, expect } from 'vitest'
import {
  getKpiStatusColors,
  getAnomalySeverityColors,
  getAnomalySeverityLabel,
  getAnomalyResolutionColors,
  getAnomalyResolutionLabel,
  getHealthScoreStatus,
  getConversionRateStatus,
  getTimeToFillStatus,
  getProgressColor,
  convertComponentScoreToPercentage,
  sortAnomaliesBySeverity,
  countAnomaliesBySeverity,
  filterOpenAnomalies,
  filterResolvedAnomalies,
  formatDateBR,
  formatDateTimeBR,
  formatResolutionNotes,
  truncateAnomalyId,
} from '@/lib/integridade'
import type { Anomaly, AnomalySeverity } from '@/lib/integridade'

describe('getKpiStatusColors', () => {
  it('returns success semantic colors for good status', () => {
    const colors = getKpiStatusColors('good')
    expect(colors.border).toContain('status-success')
    expect(colors.text).toContain('status-success')
  })

  it('returns warning semantic colors for warn status', () => {
    const colors = getKpiStatusColors('warn')
    expect(colors.border).toContain('status-warning')
    expect(colors.text).toContain('status-warning')
  })

  it('returns error semantic colors for bad status', () => {
    const colors = getKpiStatusColors('bad')
    expect(colors.border).toContain('status-error')
    expect(colors.text).toContain('status-error')
  })

  it('returns gray fallback colors for unknown status', () => {
    const colors = getKpiStatusColors('unknown' as any)
    expect(colors.border).toContain('gray')
    expect(colors.text).toContain('gray')
  })
})

describe('getAnomalySeverityColors', () => {
  it('returns error semantic colors for high severity', () => {
    const colors = getAnomalySeverityColors('high')
    expect(colors.icon).toContain('status-error')
    expect(colors.badge).toContain('status-error')
  })

  it('returns warning semantic colors for medium severity', () => {
    const colors = getAnomalySeverityColors('medium')
    expect(colors.icon).toContain('status-warning')
    expect(colors.badge).toContain('status-warning')
  })

  it('returns info semantic colors for low severity', () => {
    const colors = getAnomalySeverityColors('low')
    expect(colors.icon).toContain('status-info')
    expect(colors.badge).toContain('status-info')
  })

  it('returns gray fallback colors for unknown severity', () => {
    const colors = getAnomalySeverityColors('unknown' as any)
    expect(colors.icon).toContain('gray')
    expect(colors.badge).toContain('gray')
  })
})

describe('getAnomalySeverityLabel', () => {
  it('returns Alta for high', () => {
    expect(getAnomalySeverityLabel('high')).toBe('Alta')
  })

  it('returns Media for medium', () => {
    expect(getAnomalySeverityLabel('medium')).toBe('Media')
  })

  it('returns Baixa for low', () => {
    expect(getAnomalySeverityLabel('low')).toBe('Baixa')
  })

  it('returns original string for unknown severity', () => {
    expect(getAnomalySeverityLabel('unknown' as any)).toBe('unknown')
  })
})

describe('getAnomalyResolutionColors', () => {
  it('returns success semantic colors for resolved', () => {
    const colors = getAnomalyResolutionColors(true)
    expect(colors.bg).toContain('status-success')
    expect(colors.text).toContain('status-success')
  })

  it('returns warning semantic colors for open', () => {
    const colors = getAnomalyResolutionColors(false)
    expect(colors.bg).toContain('status-warning')
    expect(colors.text).toContain('status-warning')
  })
})

describe('getAnomalyResolutionLabel', () => {
  it('returns Resolvida for resolved', () => {
    expect(getAnomalyResolutionLabel(true)).toBe('Resolvida')
  })

  it('returns Aberta for open', () => {
    expect(getAnomalyResolutionLabel(false)).toBe('Aberta')
  })
})

describe('getHealthScoreStatus', () => {
  it('returns good for score >= 80', () => {
    expect(getHealthScoreStatus(80)).toBe('good')
    expect(getHealthScoreStatus(90)).toBe('good')
    expect(getHealthScoreStatus(100)).toBe('good')
  })

  it('returns warn for score between 60 and 79', () => {
    expect(getHealthScoreStatus(60)).toBe('warn')
    expect(getHealthScoreStatus(70)).toBe('warn')
    expect(getHealthScoreStatus(79)).toBe('warn')
  })

  it('returns bad for score < 60', () => {
    expect(getHealthScoreStatus(59)).toBe('bad')
    expect(getHealthScoreStatus(30)).toBe('bad')
    expect(getHealthScoreStatus(0)).toBe('bad')
  })
})

describe('getConversionRateStatus', () => {
  it('returns good for rate >= 30', () => {
    expect(getConversionRateStatus(30)).toBe('good')
    expect(getConversionRateStatus(50)).toBe('good')
  })

  it('returns warn for rate between 20 and 29', () => {
    expect(getConversionRateStatus(20)).toBe('warn')
    expect(getConversionRateStatus(25)).toBe('warn')
    expect(getConversionRateStatus(29)).toBe('warn')
  })

  it('returns bad for rate < 20', () => {
    expect(getConversionRateStatus(19)).toBe('bad')
    expect(getConversionRateStatus(10)).toBe('bad')
    expect(getConversionRateStatus(0)).toBe('bad')
  })
})

describe('getTimeToFillStatus', () => {
  it('returns good for hours <= 4', () => {
    expect(getTimeToFillStatus(4)).toBe('good')
    expect(getTimeToFillStatus(2)).toBe('good')
    expect(getTimeToFillStatus(0)).toBe('good')
  })

  it('returns warn for hours between 5 and 8', () => {
    expect(getTimeToFillStatus(5)).toBe('warn')
    expect(getTimeToFillStatus(6)).toBe('warn')
    expect(getTimeToFillStatus(8)).toBe('warn')
  })

  it('returns bad for hours > 8', () => {
    expect(getTimeToFillStatus(9)).toBe('bad')
    expect(getTimeToFillStatus(12)).toBe('bad')
    expect(getTimeToFillStatus(24)).toBe('bad')
  })
})

describe('getProgressColor', () => {
  it('returns success semantic color for percentage >= 80', () => {
    expect(getProgressColor(80)).toContain('status-success')
    expect(getProgressColor(100)).toContain('status-success')
  })

  it('returns warning semantic color for percentage between 60 and 79', () => {
    expect(getProgressColor(60)).toContain('status-warning')
    expect(getProgressColor(70)).toContain('status-warning')
    expect(getProgressColor(79)).toContain('status-warning')
  })

  it('returns error semantic color for percentage < 60', () => {
    expect(getProgressColor(59)).toContain('status-error')
    expect(getProgressColor(30)).toContain('status-error')
    expect(getProgressColor(0)).toContain('status-error')
  })
})

describe('convertComponentScoreToPercentage', () => {
  it('converts 0 to 100%', () => {
    expect(convertComponentScoreToPercentage(0)).toBe(100)
  })

  it('converts 5 to 50%', () => {
    expect(convertComponentScoreToPercentage(5)).toBe(50)
  })

  it('converts 10 to 0%', () => {
    expect(convertComponentScoreToPercentage(10)).toBe(0)
  })

  it('clamps to 0-100 range', () => {
    expect(convertComponentScoreToPercentage(-1)).toBe(100)
    expect(convertComponentScoreToPercentage(15)).toBe(0)
  })
})

describe('sortAnomaliesBySeverity', () => {
  it('sorts high severity first', () => {
    const anomalies: { severidade: AnomalySeverity }[] = [
      { severidade: 'low' },
      { severidade: 'high' },
      { severidade: 'medium' },
    ]

    const sorted = sortAnomaliesBySeverity(anomalies)

    expect(sorted[0]?.severidade).toBe('high')
    expect(sorted[1]?.severidade).toBe('medium')
    expect(sorted[2]?.severidade).toBe('low')
  })

  it('does not mutate original array', () => {
    const original: { severidade: AnomalySeverity }[] = [
      { severidade: 'low' },
      { severidade: 'high' },
    ]
    sortAnomaliesBySeverity(original)
    expect(original[0]?.severidade).toBe('low')
  })

  it('returns empty array for empty input', () => {
    expect(sortAnomaliesBySeverity([])).toEqual([])
  })
})

describe('countAnomaliesBySeverity', () => {
  it('counts anomalies by severity', () => {
    const anomalies: Anomaly[] = [
      createAnomaly('1', 'high'),
      createAnomaly('2', 'high'),
      createAnomaly('3', 'medium'),
      createAnomaly('4', 'low'),
      createAnomaly('5', 'low'),
      createAnomaly('6', 'low'),
    ]

    const counts = countAnomaliesBySeverity(anomalies)

    expect(counts.high).toBe(2)
    expect(counts.medium).toBe(1)
    expect(counts.low).toBe(3)
  })

  it('returns zeros for empty array', () => {
    const counts = countAnomaliesBySeverity([])
    expect(counts.high).toBe(0)
    expect(counts.medium).toBe(0)
    expect(counts.low).toBe(0)
  })
})

describe('filterOpenAnomalies', () => {
  it('returns only open anomalies', () => {
    const anomalies = [{ resolvida: false }, { resolvida: true }, { resolvida: false }]

    const open = filterOpenAnomalies(anomalies)

    expect(open).toHaveLength(2)
    expect(open.every((a) => !a.resolvida)).toBe(true)
  })

  it('returns empty array if all resolved', () => {
    const anomalies = [{ resolvida: true }, { resolvida: true }]
    expect(filterOpenAnomalies(anomalies)).toHaveLength(0)
  })
})

describe('filterResolvedAnomalies', () => {
  it('returns only resolved anomalies', () => {
    const anomalies = [{ resolvida: false }, { resolvida: true }, { resolvida: true }]

    const resolved = filterResolvedAnomalies(anomalies)

    expect(resolved).toHaveLength(2)
    expect(resolved.every((a) => a.resolvida)).toBe(true)
  })

  it('returns empty array if none resolved', () => {
    const anomalies = [{ resolvida: false }, { resolvida: false }]
    expect(filterResolvedAnomalies(anomalies)).toHaveLength(0)
  })
})

describe('formatDateBR', () => {
  it('formats date in pt-BR format', () => {
    const result = formatDateBR('2026-02-01T10:30:00Z')
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
  })
})

describe('formatDateTimeBR', () => {
  it('formats date and time in pt-BR format', () => {
    const result = formatDateTimeBR('2026-02-01T10:30:00Z')
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
    expect(result).toMatch(/\d{2}:\d{2}/)
  })
})

describe('formatResolutionNotes', () => {
  it('adds [Corrigido] prefix for corrigido type', () => {
    const result = formatResolutionNotes('corrigido', 'Bug fixed')
    expect(result).toBe('[Corrigido] Bug fixed')
  })

  it('adds [Falso Positivo] prefix for falso_positivo type', () => {
    const result = formatResolutionNotes('falso_positivo', 'Not a real issue')
    expect(result).toBe('[Falso Positivo] Not a real issue')
  })

  it('handles empty notes', () => {
    expect(formatResolutionNotes('corrigido', '')).toBe('[Corrigido] ')
  })
})

describe('truncateAnomalyId', () => {
  it('truncates to 8 characters by default', () => {
    const id = '12345678901234567890'
    expect(truncateAnomalyId(id)).toBe('12345678')
  })

  it('truncates to specified length', () => {
    const id = '12345678901234567890'
    expect(truncateAnomalyId(id, 4)).toBe('1234')
  })

  it('returns full id if shorter than length', () => {
    const id = '1234'
    expect(truncateAnomalyId(id, 8)).toBe('1234')
  })
})

// Helper function to create anomaly for tests
function createAnomaly(id: string, severidade: AnomalySeverity): Anomaly {
  return {
    id,
    tipo: 'test',
    entidade: 'test',
    entidadeId: 'test-id',
    severidade,
    mensagem: 'Test message',
    criadaEm: '2026-01-01T00:00:00Z',
    resolvida: false,
  }
}
