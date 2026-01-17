/**
 * Shared formatters for dashboard export (PDF and CSV)
 *
 * These functions contain business logic for formatting dashboard data.
 * Extracted from pdf-generator.ts and csv-generator.ts to:
 * 1. Avoid code duplication (DRY)
 * 2. Enable proper unit testing
 * 3. Ensure consistency between export formats
 */

/**
 * Formats a date string for display (DD/MM/YYYY).
 *
 * @param isoDate - ISO date string
 * @returns Formatted date in pt-BR locale
 */
export function formatExportDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('pt-BR')
}

/**
 * Formats a date and time for display.
 *
 * @param date - Date object
 * @returns Formatted date and time in pt-BR locale
 */
export function formatExportDateTime(date: Date): string {
  return date.toLocaleString('pt-BR')
}

/**
 * Formats a numeric value with its unit.
 *
 * @param value - Numeric value
 * @param unit - Unit type (percent, %, s, seconds, currency, or empty)
 * @returns Formatted value string
 */
export function formatValue(value: number, unit: string): string {
  if (unit === 'percent') return `${value.toFixed(1)}%`
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 's') return `${value}s`
  if (unit === 'seconds') return `${value}s`
  if (unit === 'currency') return `R$ ${value.toFixed(2)}`
  return value.toString()
}

/**
 * Calculates percentage change between two values.
 *
 * @param current - Current value
 * @param previous - Previous value
 * @returns Formatted change string with + or - prefix, or N/A if previous is 0
 */
export function calculateChange(current: number, previous: number): string {
  if (previous === 0) return 'N/A'
  const change = ((current - previous) / previous) * 100
  return change >= 0 ? `+${change.toFixed(0)}%` : `${change.toFixed(0)}%`
}

/**
 * Determines if a metric has reached its goal.
 *
 * @param value - Current value
 * @param meta - Target value
 * @returns 'Atingida' if value >= meta, otherwise 'Abaixo'
 */
export function getMetaStatus(value: number, meta: number): string {
  return value >= meta ? 'Atingida' : 'Abaixo'
}

/**
 * Maps chip status to display color.
 *
 * @param status - Chip status string
 * @returns Hex color code
 */
export function getStatusColor(status: string): string {
  const COLORS = {
    success: '#16a34a',
    primary: '#1e40af',
    warning: '#ca8a04',
    danger: '#dc2626',
    muted: '#6b7280',
  }

  switch (status) {
    case 'active':
      return COLORS.success
    case 'ready':
      return COLORS.primary
    case 'warming':
      return COLORS.warning
    case 'degraded':
      return COLORS.danger
    default:
      return COLORS.muted
  }
}

/**
 * Escapes a string for CSV (handles commas, quotes, and newlines).
 *
 * @param value - String to escape
 * @returns Escaped string safe for CSV
 */
export function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}
