/**
 * Tests for lib/dashboard/calculations.ts
 */

import { describe, expect, it } from 'vitest'
import {
  calculatePercentChange,
  calculatePercentageChange,
  calculateRate,
  formatChange,
  getPeriodDates,
  getTrendStatus,
  isTrendPositive,
  roundTo,
  validatePeriod,
} from '@/lib/dashboard/calculations'

describe('getPeriodDates', () => {
  it('should return 1 day for "24h" period', () => {
    const result = getPeriodDates('24h')
    expect(result.days).toBe(1)
  })

  it('should return 7 days for "7d" period', () => {
    const result = getPeriodDates('7d')
    expect(result.days).toBe(7)
  })

  it('should return 14 days for "14d" period', () => {
    const result = getPeriodDates('14d')
    expect(result.days).toBe(14)
  })

  it('should return 30 days for "30d" period', () => {
    const result = getPeriodDates('30d')
    expect(result.days).toBe(30)
  })

  it('should default to 7 days for unknown period', () => {
    const result = getPeriodDates('unknown')
    expect(result.days).toBe(7)
  })

  it('should return valid ISO date strings', () => {
    const result = getPeriodDates('7d')
    expect(() => new Date(result.currentStart)).not.toThrow()
    expect(() => new Date(result.currentEnd)).not.toThrow()
    expect(() => new Date(result.previousStart)).not.toThrow()
    expect(() => new Date(result.previousEnd)).not.toThrow()
  })

  it('should have currentEnd after currentStart', () => {
    const result = getPeriodDates('7d')
    expect(new Date(result.currentEnd).getTime()).toBeGreaterThan(
      new Date(result.currentStart).getTime()
    )
  })

  it('should have previousEnd equal to currentStart', () => {
    const result = getPeriodDates('7d')
    expect(result.previousEnd).toBe(result.currentStart)
  })
})

describe('calculatePercentChange', () => {
  it('should calculate positive change correctly', () => {
    expect(calculatePercentChange(150, 100)).toBe(50)
  })

  it('should calculate negative change correctly', () => {
    expect(calculatePercentChange(50, 100)).toBe(-50)
  })

  it('should return 0 when previous is 0 and current is positive', () => {
    expect(calculatePercentChange(50, 0)).toBe(0)
  })

  it('should return 0 when previous is 0 and current is 0', () => {
    expect(calculatePercentChange(0, 0)).toBe(0)
  })

  it('should return 0 when both values are the same', () => {
    expect(calculatePercentChange(100, 100)).toBe(0)
  })

  it('should handle decimal results', () => {
    expect(calculatePercentChange(110, 100)).toBe(10)
  })
})

describe('calculateRate', () => {
  it('should calculate rate correctly', () => {
    expect(calculateRate(50, 100)).toBe(50)
  })

  it('should return 0 when denominator is 0', () => {
    expect(calculateRate(50, 0)).toBe(0)
  })

  it('should handle 100% rate', () => {
    expect(calculateRate(100, 100)).toBe(100)
  })

  it('should handle rates over 100%', () => {
    expect(calculateRate(150, 100)).toBe(150)
  })

  it('should handle decimal results', () => {
    expect(calculateRate(1, 3)).toBeCloseTo(33.3, 1)
  })
})

describe('roundTo', () => {
  it('should round to 1 decimal by default', () => {
    expect(roundTo(3.456)).toBe(3.5)
  })

  it('should round to specified decimals', () => {
    expect(roundTo(3.456, 2)).toBe(3.46)
  })

  it('should round to 0 decimals', () => {
    expect(roundTo(3.456, 0)).toBe(3)
  })

  it('should handle negative numbers', () => {
    expect(roundTo(-3.456, 1)).toBe(-3.5)
  })

  it('should handle whole numbers', () => {
    expect(roundTo(5, 2)).toBe(5)
  })
})

describe('validatePeriod', () => {
  it('should return "24h" for valid "24h" input', () => {
    expect(validatePeriod('24h')).toBe('24h')
  })

  it('should return "7d" for valid "7d" input', () => {
    expect(validatePeriod('7d')).toBe('7d')
  })

  it('should return "14d" for valid "14d" input', () => {
    expect(validatePeriod('14d')).toBe('14d')
  })

  it('should return "30d" for valid "30d" input', () => {
    expect(validatePeriod('30d')).toBe('30d')
  })

  it('should return default "7d" for invalid input', () => {
    expect(validatePeriod('invalid')).toBe('7d')
  })

  it('should return default "7d" for null input', () => {
    expect(validatePeriod(null)).toBe('7d')
  })

  it('should return default "7d" for empty string', () => {
    expect(validatePeriod('')).toBe('7d')
  })
})

describe('calculatePercentageChange', () => {
  it('should calculate positive change', () => {
    expect(calculatePercentageChange(120, 100)).toBe(20)
  })

  it('should calculate negative change', () => {
    expect(calculatePercentageChange(80, 100)).toBe(-20)
  })

  it('should return null when previous is 0', () => {
    expect(calculatePercentageChange(100, 0)).toBeNull()
  })

  it('should return 0 for no change', () => {
    expect(calculatePercentageChange(100, 100)).toBe(0)
  })
})

describe('isTrendPositive', () => {
  it('should return true for positive change (default)', () => {
    expect(isTrendPositive(10)).toBe(true)
  })

  it('should return false for negative change (default)', () => {
    expect(isTrendPositive(-10)).toBe(false)
  })

  it('should return true for negative change when lesserIsBetter', () => {
    expect(isTrendPositive(-10, true)).toBe(true)
  })

  it('should return false for positive change when lesserIsBetter', () => {
    expect(isTrendPositive(10, true)).toBe(false)
  })

  it('should return false for zero change', () => {
    expect(isTrendPositive(0)).toBe(false)
  })
})

describe('formatChange', () => {
  it('should format positive change with + prefix', () => {
    expect(formatChange(15.5)).toBe('+16%')
  })

  it('should format negative change without + prefix', () => {
    expect(formatChange(-8.3)).toBe('-8%')
  })

  it('should return "N/A" for null', () => {
    expect(formatChange(null)).toBe('N/A')
  })

  it('should format zero change', () => {
    expect(formatChange(0)).toBe('0%')
  })

  it('should round to integer', () => {
    expect(formatChange(15.9)).toBe('+16%')
  })
})

describe('getTrendStatus', () => {
  it('should return "positive" for positive change', () => {
    expect(getTrendStatus(10)).toBe('positive')
  })

  it('should return "negative" for negative change', () => {
    expect(getTrendStatus(-10)).toBe('negative')
  })

  it('should return "neutral" for null', () => {
    expect(getTrendStatus(null)).toBe('neutral')
  })

  it('should return "neutral" for small changes (< 1%)', () => {
    expect(getTrendStatus(0.5)).toBe('neutral')
    expect(getTrendStatus(-0.5)).toBe('neutral')
  })

  it('should invert when lesserIsBetter is true', () => {
    expect(getTrendStatus(-10, true)).toBe('positive')
    expect(getTrendStatus(10, true)).toBe('negative')
  })
})
