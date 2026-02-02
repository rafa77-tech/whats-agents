import { describe, it, expect } from 'vitest'
import {
  formatCurrency,
  parseShiftDate,
  getStatusBadgeColor,
  getStatusIndicatorColor,
  getStatusLabel,
  formatTimeRange,
  formatReservasCount,
} from '@/lib/vagas/formatters'

describe('formatCurrency', () => {
  // Note: Intl.NumberFormat may use non-breaking spaces (U+00A0) instead of regular spaces
  // We test that the output contains the expected parts

  it('formats positive values correctly', () => {
    expect(formatCurrency(1500)).toContain('R$')
    expect(formatCurrency(1500)).toContain('1.500,00')
    expect(formatCurrency(2500.5)).toContain('2.500,50')
    expect(formatCurrency(100)).toContain('100,00')
  })

  it('formats zero correctly', () => {
    expect(formatCurrency(0)).toContain('R$')
    expect(formatCurrency(0)).toContain('0,00')
  })

  it('formats decimal values correctly', () => {
    expect(formatCurrency(1234.56)).toContain('1.234,56')
    expect(formatCurrency(0.99)).toContain('0,99')
  })

  it('formats large values correctly', () => {
    expect(formatCurrency(1000000)).toContain('1.000.000,00')
  })

  it('formats negative values correctly', () => {
    const result = formatCurrency(-500)
    expect(result).toContain('R$')
    expect(result).toContain('500,00')
    // Should indicate negative (either with - or parentheses)
    expect(result.includes('-') || result.includes('(')).toBe(true)
  })
})

describe('parseShiftDate', () => {
  it('parses YYYY-MM-DD format correctly', () => {
    const date = parseShiftDate('2026-01-15')
    expect(date.getFullYear()).toBe(2026)
    expect(date.getMonth()).toBe(0) // January = 0
    expect(date.getDate()).toBe(15)
  })

  it('handles different months correctly', () => {
    const dec = parseShiftDate('2026-12-25')
    expect(dec.getMonth()).toBe(11) // December = 11
    expect(dec.getDate()).toBe(25)
  })

  it('creates date at midnight local time', () => {
    const date = parseShiftDate('2026-06-01')
    expect(date.getHours()).toBe(0)
    expect(date.getMinutes()).toBe(0)
    expect(date.getSeconds()).toBe(0)
  })
})

describe('getStatusBadgeColor', () => {
  it('returns correct color for each status', () => {
    expect(getStatusBadgeColor('aberta')).toBe('bg-status-success text-status-success-foreground')
    expect(getStatusBadgeColor('reservada')).toBe(
      'bg-status-warning text-status-warning-foreground'
    )
    expect(getStatusBadgeColor('confirmada')).toBe('bg-status-info text-status-info-foreground')
    expect(getStatusBadgeColor('cancelada')).toBe('bg-status-error text-status-error-foreground')
    expect(getStatusBadgeColor('realizada')).toBe(
      'bg-status-neutral text-status-neutral-foreground'
    )
    expect(getStatusBadgeColor('fechada')).toBe('bg-status-neutral text-status-neutral-foreground')
  })

  it('returns default color for unknown status', () => {
    expect(getStatusBadgeColor('unknown')).toBe('bg-status-neutral text-status-neutral-foreground')
    expect(getStatusBadgeColor('')).toBe('bg-status-neutral text-status-neutral-foreground')
  })
})

describe('getStatusIndicatorColor', () => {
  it('returns correct indicator color for each status', () => {
    expect(getStatusIndicatorColor('aberta')).toBe('bg-status-success-solid')
    expect(getStatusIndicatorColor('reservada')).toBe('bg-status-warning-solid')
    expect(getStatusIndicatorColor('confirmada')).toBe('bg-status-info-solid')
    expect(getStatusIndicatorColor('cancelada')).toBe('bg-status-error-solid')
    expect(getStatusIndicatorColor('realizada')).toBe('bg-status-neutral-solid')
    expect(getStatusIndicatorColor('fechada')).toBe('bg-status-neutral-solid')
  })

  it('returns default color for unknown status', () => {
    expect(getStatusIndicatorColor('unknown')).toBe('bg-status-neutral-solid')
    expect(getStatusIndicatorColor('')).toBe('bg-status-neutral-solid')
  })
})

describe('getStatusLabel', () => {
  it('returns correct label for each status', () => {
    expect(getStatusLabel('aberta')).toBe('Aberta')
    expect(getStatusLabel('reservada')).toBe('Reservada')
    expect(getStatusLabel('confirmada')).toBe('Confirmada')
    expect(getStatusLabel('cancelada')).toBe('Cancelada')
    expect(getStatusLabel('realizada')).toBe('Realizada')
    expect(getStatusLabel('fechada')).toBe('Fechada')
  })

  it('returns raw status for unknown status', () => {
    expect(getStatusLabel('unknown')).toBe('unknown')
    expect(getStatusLabel('custom_status')).toBe('custom_status')
  })
})

describe('formatTimeRange', () => {
  it('formats time range correctly', () => {
    expect(formatTimeRange('08:00', '18:00')).toBe('08:00 - 18:00')
    expect(formatTimeRange('19:00', '07:00')).toBe('19:00 - 07:00')
    expect(formatTimeRange('00:00', '23:59')).toBe('00:00 - 23:59')
  })
})

describe('formatReservasCount', () => {
  it('returns empty string for zero', () => {
    expect(formatReservasCount(0)).toBe('')
  })

  it('returns singular for one reservation', () => {
    expect(formatReservasCount(1)).toBe('1 reserva')
  })

  it('returns plural for multiple reservations', () => {
    expect(formatReservasCount(2)).toBe('2 reservas')
    expect(formatReservasCount(5)).toBe('5 reservas')
    expect(formatReservasCount(100)).toBe('100 reservas')
  })
})
