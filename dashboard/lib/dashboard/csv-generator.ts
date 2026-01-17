/**
 * CSV Generator for Dashboard Export - Sprint 33 E16
 *
 * Generates CSV reports with all dashboard metrics.
 */

import { type DashboardExportData } from '@/types/dashboard'
import {
  formatExportDate,
  formatExportDateTime,
  formatValue,
  calculateChange,
  getMetaStatus,
  escapeCSV,
} from './formatters'

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
  lines.push(`Periodo: ${formatExportDate(period.start)} a ${formatExportDate(period.end)}`)
  lines.push(`Gerado em: ${formatExportDateTime(new Date())}`)
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
