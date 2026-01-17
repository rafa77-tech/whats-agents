/**
 * PDF Generator for Dashboard Export - Sprint 33 E17
 *
 * Generates PDF reports with all dashboard metrics using jsPDF.
 */

import { jsPDF } from 'jspdf'
import { type DashboardExportData } from '@/types/dashboard'

// Colors
const COLORS = {
  primary: '#1e40af', // blue-800
  secondary: '#6b7280', // gray-500
  success: '#16a34a', // green-600
  warning: '#ca8a04', // yellow-600
  danger: '#dc2626', // red-600
  text: '#111827', // gray-900
  textMuted: '#6b7280', // gray-500
  border: '#e5e7eb', // gray-200
}

interface TableColumn {
  header: string
  width: number
}

/**
 * Generates a complete PDF report from dashboard data.
 *
 * @param data - Dashboard export data
 * @returns PDF as ArrayBuffer
 */
export function generateDashboardPDF(data: DashboardExportData): ArrayBuffer {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  })

  const pageWidth = doc.internal.pageSize.getWidth()
  const margin = 20
  const contentWidth = pageWidth - margin * 2
  let yPosition = margin

  // Header
  yPosition = drawHeader(doc, data, yPosition, margin, contentWidth)

  // Main Metrics Section
  yPosition = drawSection(doc, 'METRICAS PRINCIPAIS', yPosition, margin)
  yPosition = drawMetricsTable(doc, data.metrics, yPosition, margin)

  // Quality Section
  yPosition = drawSection(doc, 'QUALIDADE DA PERSONA', yPosition, margin)
  yPosition = drawQualityTable(doc, data.quality, yPosition, margin)

  // Check if we need a new page
  if (yPosition > 200) {
    doc.addPage()
    yPosition = margin
  }

  // Chips Section
  yPosition = drawSection(doc, 'POOL DE CHIPS', yPosition, margin)
  yPosition = drawChipsTable(doc, data.chips, yPosition, margin)

  // Check if we need a new page
  if (yPosition > 220) {
    doc.addPage()
    yPosition = margin
  }

  // Funnel Section
  yPosition = drawSection(doc, 'FUNIL DE CONVERSAO', yPosition, margin)
  yPosition = drawFunnelTable(doc, data.funnel, yPosition, margin)

  // Footer
  drawFooter(doc)

  return doc.output('arraybuffer')
}

/**
 * Draws the document header with title and period info.
 */
function drawHeader(
  doc: jsPDF,
  data: DashboardExportData,
  y: number,
  margin: number,
  _contentWidth: number
): number {
  // Title
  doc.setFontSize(20)
  doc.setTextColor(COLORS.primary)
  doc.text('Relatorio Dashboard Julia', margin, y)
  y += 10

  // Period
  doc.setFontSize(11)
  doc.setTextColor(COLORS.textMuted)
  const periodStart = formatDate(data.period.start)
  const periodEnd = formatDate(data.period.end)
  doc.text(`Periodo: ${periodStart} a ${periodEnd}`, margin, y)
  y += 6

  // Generated date
  doc.text(`Gerado em: ${formatDateTime(new Date())}`, margin, y)
  y += 10

  // Separator line
  doc.setDrawColor(COLORS.border)
  doc.setLineWidth(0.5)
  doc.line(margin, y, doc.internal.pageSize.getWidth() - margin, y)
  y += 10

  return y
}

/**
 * Draws a section header.
 */
function drawSection(doc: jsPDF, title: string, y: number, margin: number): number {
  doc.setFontSize(12)
  doc.setTextColor(COLORS.primary)
  doc.setFont('helvetica', 'bold')
  doc.text(title, margin, y)
  doc.setFont('helvetica', 'normal')
  return y + 8
}

/**
 * Draws the main metrics table.
 */
function drawMetricsTable(
  doc: jsPDF,
  metrics: DashboardExportData['metrics'],
  y: number,
  margin: number
): number {
  const columns: TableColumn[] = [
    { header: 'Metrica', width: 45 },
    { header: 'Atual', width: 25 },
    { header: 'Anterior', width: 25 },
    { header: 'Variacao', width: 25 },
    { header: 'Meta', width: 25 },
    { header: 'Status', width: 25 },
  ]

  y = drawTableHeader(doc, columns, y, margin)

  metrics.forEach((m) => {
    const change = calculateChange(m.current, m.previous)
    const status = m.current >= m.meta ? 'Atingida' : 'Abaixo'
    const statusColor = m.current >= m.meta ? COLORS.success : COLORS.warning

    const row = [
      m.name,
      formatValue(m.current, m.unit),
      formatValue(m.previous, m.unit),
      change,
      formatValue(m.meta, m.unit),
      status,
    ]

    y = drawTableRow(doc, columns, row, y, margin, [null, null, null, null, null, statusColor])
  })

  return y + 8
}

/**
 * Draws the quality metrics table.
 */
function drawQualityTable(
  doc: jsPDF,
  quality: DashboardExportData['quality'],
  y: number,
  margin: number
): number {
  const columns: TableColumn[] = [
    { header: 'Metrica', width: 45 },
    { header: 'Atual', width: 30 },
    { header: 'Anterior', width: 30 },
    { header: 'Variacao', width: 30 },
    { header: 'Meta', width: 35 },
  ]

  y = drawTableHeader(doc, columns, y, margin)

  quality.forEach((q) => {
    const change = calculateChange(q.current, q.previous)

    const row = [
      q.name,
      formatValue(q.current, q.unit),
      formatValue(q.previous, q.unit),
      change,
      String(q.meta),
    ]

    y = drawTableRow(doc, columns, row, y, margin)
  })

  return y + 8
}

/**
 * Draws the chips table.
 */
function drawChipsTable(
  doc: jsPDF,
  chips: DashboardExportData['chips'],
  y: number,
  margin: number
): number {
  const columns: TableColumn[] = [
    { header: 'Chip', width: 35 },
    { header: 'Status', width: 25 },
    { header: 'Trust', width: 20 },
    { header: 'Msgs Hoje', width: 30 },
    { header: 'Taxa Resp', width: 30 },
    { header: 'Erros 24h', width: 25 },
  ]

  y = drawTableHeader(doc, columns, y, margin)

  chips.forEach((c) => {
    const statusColor = getStatusColor(c.status)

    const row = [
      c.name,
      c.status,
      String(c.trust),
      String(c.messagesToday),
      `${c.responseRate.toFixed(1)}%`,
      String(c.errors),
    ]

    y = drawTableRow(doc, columns, row, y, margin, [
      null,
      statusColor,
      null,
      null,
      null,
      c.errors > 0 ? COLORS.danger : null,
    ])
  })

  return y + 8
}

/**
 * Draws the conversion funnel table.
 */
function drawFunnelTable(
  doc: jsPDF,
  funnel: DashboardExportData['funnel'],
  y: number,
  margin: number
): number {
  const columns: TableColumn[] = [
    { header: 'Etapa', width: 45 },
    { header: 'Quantidade', width: 40 },
    { header: 'Porcentagem', width: 40 },
    { header: 'Variacao', width: 40 },
  ]

  y = drawTableHeader(doc, columns, y, margin)

  funnel.forEach((f) => {
    const changeText = f.change >= 0 ? `+${f.change.toFixed(0)}%` : `${f.change.toFixed(0)}%`
    const changeColor = f.change >= 0 ? COLORS.success : COLORS.danger

    const row = [f.stage, String(f.count), `${f.percentage.toFixed(1)}%`, changeText]

    y = drawTableRow(doc, columns, row, y, margin, [null, null, null, changeColor])
  })

  return y + 8
}

/**
 * Draws a table header row.
 */
function drawTableHeader(doc: jsPDF, columns: TableColumn[], y: number, margin: number): number {
  doc.setFontSize(9)
  doc.setTextColor(COLORS.textMuted)
  doc.setFont('helvetica', 'bold')

  let x = margin
  columns.forEach((col) => {
    doc.text(col.header, x, y)
    x += col.width
  })

  doc.setFont('helvetica', 'normal')
  y += 2

  // Header underline
  doc.setDrawColor(COLORS.border)
  doc.setLineWidth(0.3)
  doc.line(margin, y, margin + columns.reduce((sum, c) => sum + c.width, 0), y)

  return y + 5
}

/**
 * Draws a table data row.
 */
function drawTableRow(
  doc: jsPDF,
  columns: TableColumn[],
  values: string[],
  y: number,
  margin: number,
  colors?: (string | null)[]
): number {
  doc.setFontSize(9)

  let x = margin
  values.forEach((value, i) => {
    const color = colors?.[i]
    if (color) {
      doc.setTextColor(color)
    } else {
      doc.setTextColor(COLORS.text)
    }
    doc.text(value, x, y)
    x += columns[i]?.width ?? 30
  })

  return y + 6
}

/**
 * Draws the page footer.
 */
function drawFooter(doc: jsPDF): void {
  const pageHeight = doc.internal.pageSize.getHeight()
  const pageWidth = doc.internal.pageSize.getWidth()
  const totalPages = doc.getNumberOfPages()

  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i)
    doc.setFontSize(8)
    doc.setTextColor(COLORS.textMuted)
    doc.text(`Pagina ${i} de ${totalPages}`, pageWidth / 2, pageHeight - 10, { align: 'center' })
    doc.text('Revoluna - Dashboard Julia', 20, pageHeight - 10)
  }
}

// Helper functions

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('pt-BR')
}

function formatDateTime(date: Date): string {
  return date.toLocaleString('pt-BR')
}

function formatValue(value: number, unit: string): string {
  if (unit === 'percent') return `${value.toFixed(1)}%`
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 's') return `${value}s`
  if (unit === 'seconds') return `${value}s`
  if (unit === 'currency') return `R$ ${value.toFixed(2)}`
  return value.toString()
}

function calculateChange(current: number, previous: number): string {
  if (previous === 0) return 'N/A'
  const change = ((current - previous) / previous) * 100
  return change >= 0 ? `+${change.toFixed(0)}%` : `${change.toFixed(0)}%`
}

function getStatusColor(status: string): string {
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
      return COLORS.textMuted
  }
}
