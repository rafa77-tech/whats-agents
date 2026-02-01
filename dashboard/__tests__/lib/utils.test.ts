/**
 * Tests for lib/utils/index.ts
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { cn, formatDate, formatDateTime, formatRelativeTime, formatPhone } from '@/lib/utils'

describe('cn (className merger)', () => {
  it('should merge class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('should handle conditional classes', () => {
    expect(cn('foo', true && 'bar', false && 'baz')).toBe('foo bar')
  })

  it('should handle arrays', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar')
  })

  it('should handle objects', () => {
    expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz')
  })

  it('should merge Tailwind classes correctly', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4')
  })

  it('should handle empty inputs', () => {
    expect(cn()).toBe('')
  })

  it('should handle undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })
})

describe('formatDate', () => {
  it('should format Date object', () => {
    const date = new Date('2025-01-15T10:30:00')
    const result = formatDate(date)
    expect(result).toMatch(/15\/01\/2025/)
  })

  it('should format ISO string', () => {
    const result = formatDate('2025-12-25T00:00:00')
    expect(result).toMatch(/25\/12\/2025/)
  })

  it('should handle different date formats', () => {
    const date = new Date(2025, 5, 1) // June 1, 2025 (month is 0-indexed)
    const result = formatDate(date)
    expect(result).toMatch(/01\/06\/2025/)
  })
})

describe('formatDateTime', () => {
  it('should format Date object with time', () => {
    const date = new Date('2025-01-15T10:30:00')
    const result = formatDateTime(date)
    expect(result).toMatch(/15\/01\/2025/)
    expect(result).toMatch(/10:30/)
  })

  it('should format ISO string with time', () => {
    const result = formatDateTime('2025-12-25T14:45:00')
    expect(result).toMatch(/25\/12\/2025/)
    expect(result).toMatch(/14:45/)
  })
})

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-15T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should return "agora" for less than 60 seconds', () => {
    const date = new Date('2025-01-15T11:59:30')
    expect(formatRelativeTime(date)).toBe('agora')
  })

  it('should return minutes for less than 1 hour', () => {
    const date = new Date('2025-01-15T11:30:00')
    expect(formatRelativeTime(date)).toBe('30min')
  })

  it('should return hours for less than 1 day', () => {
    const date = new Date('2025-01-15T09:00:00')
    expect(formatRelativeTime(date)).toBe('3h')
  })

  it('should return days for more than 1 day', () => {
    const date = new Date('2025-01-13T12:00:00')
    expect(formatRelativeTime(date)).toBe('2d')
  })

  it('should handle string input', () => {
    const result = formatRelativeTime('2025-01-15T11:55:00')
    expect(result).toBe('5min')
  })
})

describe('formatPhone', () => {
  it('should format 11-digit phone with country code', () => {
    expect(formatPhone('5511999999999')).toBe('(11) 99999-9999')
  })

  it('should format 11-digit phone without country code', () => {
    expect(formatPhone('11999999999')).toBe('(11) 99999-9999')
  })

  it('should handle phone with special characters', () => {
    expect(formatPhone('(11) 99999-9999')).toBe('(11) 99999-9999')
  })

  it('should handle phone with dashes and spaces', () => {
    expect(formatPhone('11 99999-9999')).toBe('(11) 99999-9999')
  })

  it('should return original if less than 11 digits', () => {
    expect(formatPhone('1199999')).toBe('1199999')
  })

  it('should handle phone with +55 prefix', () => {
    expect(formatPhone('+5511999999999')).toBe('(11) 99999-9999')
  })

  it('should extract last 11 digits for longer numbers', () => {
    expect(formatPhone('005511999999999')).toBe('(11) 99999-9999')
  })

  it('should handle empty string', () => {
    expect(formatPhone('')).toBe('')
  })

  it('should handle 10-digit phone (landline)', () => {
    // 10-digit phones don't match the 11-digit format, returns sliced version
    const result = formatPhone('1134567890')
    expect(result).toBe('1134567890')
  })
})
