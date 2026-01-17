/**
 * CSV Generator for Dashboard Export - Sprint 33 E16
 *
 * Generates CSV reports with all dashboard metrics.
 */

import { type DashboardExportData } from '@/types/dashboard'

/**
 * Generates a complete CSV report from dashboard data.
 *
 * @param data - Dashboard export data
 * @returns CSV string with BOM for Excel compatibility
 */
export function generateDashboardCSV(data: DashboardExportData): string {
  const lines: string[] = []
  const { period, metrics, quality, chips, funnel } = data

  // Header
  lines.push('Relatorio Dashboard Julia')
  lines.push(`Periodo: ${formatDate(period.start)} a ${formatDate(period.end)}`)
  lines.push(`Gerado em: ${formatDateTime(new Date())}`)
  lines.push('')

  // Metricas Principais
  lines.push('METRICAS PRINCIPAIS')
  lines.push('Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status')
  metrics.forEach((m) => {
    const change = calculateChange(m.current, m.previous)
    const status = getMetaStatus(m.current, m.meta)
    lines.push(
      `${escapeCSV(m.name)},${formatValue(m.current, m.unit)},${formatValue(m.previous, m.unit)},${change},${formatValue(m.meta, m.unit)},${status}`
    )
  })
  lines.push('')

  // Qualidade
  lines.push('QUALIDADE DA PERSONA')
  lines.push('Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status')
  quality.forEach((q) => {
    const change = calculateChange(q.current, q.previous)
    lines.push(
      `${escapeCSV(q.name)},${formatValue(q.current, q.unit)},${formatValue(q.previous, q.unit)},${change},${escapeCSV(q.meta)},OK`
    )
  })
  lines.push('')

  // Chips
  lines.push('POOL DE CHIPS')
  lines.push('Chip,Status,Trust,Msgs Hoje,Taxa Resp,Erros 24h')
  chips.forEach((c) => {
    lines.push(
      `${escapeCSV(c.name)},${c.status},${c.trust},${c.messagesToday},${c.responseRate.toFixed(1)}%,${c.errors}`
    )
  })
  lines.push('')

  // Funil
  lines.push('FUNIL DE CONVERSAO')
  lines.push('Etapa,Quantidade,Porcentagem,Variacao')
  funnel.forEach((f) => {
    const change = f.change >= 0 ? `+${f.change.toFixed(0)}%` : `${f.change.toFixed(0)}%`
    lines.push(`${escapeCSV(f.stage)},${f.count},${f.percentage.toFixed(1)}%,${change}`)
  })

  // Add BOM for Excel UTF-8 compatibility
  const bom = '\uFEFF'
  return bom + lines.join('\n')
}

/**
 * Formats a date string for display (DD/MM/YYYY).
 */
function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('pt-BR')
}

/**
 * Formats a date and time for display.
 */
function formatDateTime(date: Date): string {
  return date.toLocaleString('pt-BR')
}

/**
 * Formats a numeric value with its unit.
 */
function formatValue(value: number, unit: string): string {
  if (unit === 'percent') return `${value.toFixed(1)}%`
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 's') return `${value}s`
  if (unit === 'seconds') return `${value}s`
  if (unit === 'currency') return `R$ ${value.toFixed(2)}`
  return value.toString()
}

/**
 * Calculates percentage change between two values.
 */
function calculateChange(current: number, previous: number): string {
  if (previous === 0) return 'N/A'
  const change = ((current - previous) / previous) * 100
  return change >= 0 ? `+${change.toFixed(0)}%` : `${change.toFixed(0)}%`
}

/**
 * Determines if a metric has reached its goal.
 */
function getMetaStatus(value: number, meta: number): string {
  return value >= meta ? 'Atingida' : 'Abaixo'
}

/**
 * Escapes a string for CSV (handles commas and quotes).
 */
function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}
