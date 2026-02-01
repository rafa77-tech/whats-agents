/**
 * Formatadores para o modulo de Auditoria
 */

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Settings } from 'lucide-react'
import { ACTION_ICONS, ACTION_LABELS } from './constants'

// =============================================================================
// Formatadores de data
// =============================================================================

/**
 * Formata data para exibicao (dd/MM HH:mm)
 */
export function formatAuditDate(dateString: string): string {
  try {
    return format(new Date(dateString), 'dd/MM HH:mm', { locale: ptBR })
  } catch {
    return dateString
  }
}

/**
 * Formata data completa (dd/MM/yyyy HH:mm:ss)
 */
export function formatAuditDateFull(dateString: string): string {
  try {
    return format(new Date(dateString), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR })
  } catch {
    return dateString
  }
}

/**
 * Formata data para nome de arquivo (yyyy-MM-dd)
 */
export function formatDateForFilename(date: Date = new Date()): string {
  return date.toISOString().split('T')[0] || ''
}

// =============================================================================
// Formatadores de acao
// =============================================================================

/**
 * Retorna o icone para uma acao
 */
export function getActionIcon(action: string) {
  return ACTION_ICONS[action] ?? Settings
}

/**
 * Retorna o label para uma acao
 */
export function getActionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action
}

// =============================================================================
// Formatadores de CSV
// =============================================================================

/**
 * Escapa string para CSV
 */
export function escapeCsvField(value: string): string {
  // Se contem virgula, aspas ou quebra de linha, envolve em aspas
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * Formata detalhes para CSV
 */
export function formatDetailsForCsv(details: Record<string, unknown>): string {
  const json = JSON.stringify(details)
  return escapeCsvField(json)
}

// =============================================================================
// Builders de URL
// =============================================================================

/**
 * Constroi URL para busca de logs
 */
export function buildAuditLogsUrl(
  baseUrl: string,
  page: number,
  perPage: number,
  filters: {
    action?: string | undefined
    actor_email?: string | undefined
    from_date?: string | undefined
    to_date?: string | undefined
  }
): string {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  })

  if (filters.action) params.set('action', filters.action)
  if (filters.actor_email) params.set('actor_email', filters.actor_email)
  if (filters.from_date) params.set('from_date', filters.from_date)
  if (filters.to_date) params.set('to_date', filters.to_date)

  return `${baseUrl}?${params}`
}

/**
 * Constroi URL para export
 */
export function buildExportUrl(
  baseUrl: string,
  filters: {
    action?: string | undefined
    actor_email?: string | undefined
    from_date?: string | undefined
    to_date?: string | undefined
  }
): string {
  const params = new URLSearchParams()

  if (filters.action) params.set('action', filters.action)
  if (filters.actor_email) params.set('actor_email', filters.actor_email)
  if (filters.from_date) params.set('from_date', filters.from_date)
  if (filters.to_date) params.set('to_date', filters.to_date)

  const queryString = params.toString()
  return queryString ? `${baseUrl}?${queryString}` : baseUrl
}
