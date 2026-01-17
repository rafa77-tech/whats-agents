/**
 * Tests for lib/dashboard/formatters.ts
 *
 * These tests ensure the business logic for formatting dashboard data
 * works correctly across both PDF and CSV export formats.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import {
  formatExportDate,
  formatExportDateTime,
  formatValue,
  calculateChange,
  getMetaStatus,
  getStatusColor,
  escapeCSV,
} from '@/lib/dashboard/formatters'

describe('formatExportDate', () => {
  it('should format ISO date to pt-BR format', () => {
    const result = formatExportDate('2025-01-15T10:30:00')
    expect(result).toMatch(/15\/01\/2025/)
  })

  it('should handle different months correctly', () => {
    const result = formatExportDate('2025-12-25T00:00:00')
    expect(result).toMatch(/25\/12\/2025/)
  })

  it('should handle year boundary', () => {
    const result = formatExportDate('2026-01-01T00:00:00')
    expect(result).toMatch(/01\/01\/2026/)
  })
})

describe('formatExportDateTime', () => {
  it('should format date with time', () => {
    const date = new Date('2025-01-15T10:30:00')
    const result = formatExportDateTime(date)
    expect(result).toMatch(/15\/01\/2025/)
    expect(result).toMatch(/10:30/)
  })

  it('should handle midnight correctly', () => {
    const date = new Date('2025-01-15T00:00:00')
    const result = formatExportDateTime(date)
    expect(result).toMatch(/00:00/)
  })
})

describe('formatValue', () => {
  describe('percentage formatting', () => {
    it('should format with "percent" unit', () => {
      expect(formatValue(35.5, 'percent')).toBe('35.5%')
    })

    it('should format with "%" unit', () => {
      expect(formatValue(85.0, '%')).toBe('85.0%')
    })

    it('should handle zero percent', () => {
      expect(formatValue(0, 'percent')).toBe('0.0%')
    })

    it('should handle 100 percent', () => {
      expect(formatValue(100, 'percent')).toBe('100.0%')
    })

    it('should round to one decimal place', () => {
      expect(formatValue(33.333, 'percent')).toBe('33.3%')
      expect(formatValue(66.666, 'percent')).toBe('66.7%')
    })
  })

  describe('time formatting', () => {
    it('should format with "s" unit', () => {
      expect(formatValue(45, 's')).toBe('45s')
    })

    it('should format with "seconds" unit', () => {
      expect(formatValue(120, 'seconds')).toBe('120s')
    })

    it('should handle zero seconds', () => {
      expect(formatValue(0, 's')).toBe('0s')
    })
  })

  describe('currency formatting', () => {
    it('should format with "currency" unit', () => {
      expect(formatValue(1500.5, 'currency')).toBe('R$ 1500.50')
    })

    it('should handle zero currency', () => {
      expect(formatValue(0, 'currency')).toBe('R$ 0.00')
    })

    it('should handle large values', () => {
      expect(formatValue(10000.99, 'currency')).toBe('R$ 10000.99')
    })

    it('should round to two decimal places', () => {
      expect(formatValue(99.999, 'currency')).toBe('R$ 100.00')
    })
  })

  describe('plain number formatting', () => {
    it('should return plain number for unknown unit', () => {
      expect(formatValue(42, 'unknown')).toBe('42')
    })

    it('should return plain number for empty unit', () => {
      expect(formatValue(100, '')).toBe('100')
    })

    it('should handle decimal numbers', () => {
      expect(formatValue(3.14159, 'other')).toBe('3.14159')
    })
  })
})

describe('calculateChange', () => {
  describe('positive changes', () => {
    it('should calculate 20% increase', () => {
      expect(calculateChange(120, 100)).toBe('+20%')
    })

    it('should calculate 50% increase', () => {
      expect(calculateChange(150, 100)).toBe('+50%')
    })

    it('should calculate 100% increase (doubling)', () => {
      expect(calculateChange(200, 100)).toBe('+100%')
    })
  })

  describe('negative changes', () => {
    it('should calculate 20% decrease', () => {
      expect(calculateChange(80, 100)).toBe('-20%')
    })

    it('should calculate 50% decrease', () => {
      expect(calculateChange(50, 100)).toBe('-50%')
    })

    it('should calculate 90% decrease', () => {
      expect(calculateChange(10, 100)).toBe('-90%')
    })
  })

  describe('no change', () => {
    it('should return +0% for equal values', () => {
      expect(calculateChange(100, 100)).toBe('+0%')
    })
  })

  describe('edge cases', () => {
    it('should return N/A when previous is zero', () => {
      expect(calculateChange(100, 0)).toBe('N/A')
    })

    it('should handle very small values', () => {
      expect(calculateChange(0.2, 0.1)).toBe('+100%')
    })

    it('should handle negative values', () => {
      // From -100 to -50 is actually a 50% increase (less negative)
      expect(calculateChange(-50, -100)).toBe('-50%')
    })

    it('should round to whole percentage', () => {
      // 105 / 100 = 5% increase, but 33/30 = 10% increase
      expect(calculateChange(33, 30)).toBe('+10%')
    })
  })
})

describe('getMetaStatus', () => {
  it('should return "Atingida" when value equals meta', () => {
    expect(getMetaStatus(100, 100)).toBe('Atingida')
  })

  it('should return "Atingida" when value exceeds meta', () => {
    expect(getMetaStatus(120, 100)).toBe('Atingida')
  })

  it('should return "Abaixo" when value is below meta', () => {
    expect(getMetaStatus(80, 100)).toBe('Abaixo')
  })

  it('should handle zero values', () => {
    expect(getMetaStatus(0, 0)).toBe('Atingida')
    expect(getMetaStatus(0, 1)).toBe('Abaixo')
  })

  it('should handle decimal precision', () => {
    expect(getMetaStatus(99.99, 100)).toBe('Abaixo')
    expect(getMetaStatus(100.01, 100)).toBe('Atingida')
  })
})

describe('getStatusColor', () => {
  it('should return green for active status', () => {
    expect(getStatusColor('active')).toBe('#16a34a')
  })

  it('should return blue for ready status', () => {
    expect(getStatusColor('ready')).toBe('#1e40af')
  })

  it('should return yellow for warming status', () => {
    expect(getStatusColor('warming')).toBe('#ca8a04')
  })

  it('should return red for degraded status', () => {
    expect(getStatusColor('degraded')).toBe('#dc2626')
  })

  it('should return gray for unknown status', () => {
    expect(getStatusColor('unknown')).toBe('#6b7280')
  })

  it('should return gray for empty status', () => {
    expect(getStatusColor('')).toBe('#6b7280')
  })

  it('should be case sensitive', () => {
    expect(getStatusColor('ACTIVE')).toBe('#6b7280') // Unknown, returns muted
  })
})

describe('escapeCSV', () => {
  describe('no escaping needed', () => {
    it('should return plain string as-is', () => {
      expect(escapeCSV('Hello World')).toBe('Hello World')
    })

    it('should handle empty string', () => {
      expect(escapeCSV('')).toBe('')
    })

    it('should handle numbers as strings', () => {
      expect(escapeCSV('12345')).toBe('12345')
    })
  })

  describe('comma handling', () => {
    it('should wrap string with comma in quotes', () => {
      expect(escapeCSV('Hello, World')).toBe('"Hello, World"')
    })

    it('should handle multiple commas', () => {
      expect(escapeCSV('a,b,c,d')).toBe('"a,b,c,d"')
    })
  })

  describe('quote handling', () => {
    it('should escape double quotes', () => {
      expect(escapeCSV('Say "Hello"')).toBe('"Say ""Hello"""')
    })

    it('should handle quotes with commas', () => {
      expect(escapeCSV('"Hello", she said')).toBe('"""Hello"", she said"')
    })
  })

  describe('newline handling', () => {
    it('should wrap string with newline in quotes', () => {
      expect(escapeCSV('Line1\nLine2')).toBe('"Line1\nLine2"')
    })

    it('should handle carriage return and newline', () => {
      expect(escapeCSV('Line1\r\nLine2')).toBe('"Line1\r\nLine2"')
    })
  })

  describe('combined special characters', () => {
    it('should handle comma, quote, and newline together', () => {
      expect(escapeCSV('Hello, "World"\nGoodbye')).toBe('"Hello, ""World""\nGoodbye"')
    })
  })
})
