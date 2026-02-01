/**
 * Formatadores para o modulo Conversas
 * Sprint 43: UX & Operacao Unificada
 */

import { CONVERSATION_STATUS_LABELS, CONTROLLED_BY_LABELS, MESSAGE_TYPE_LABELS } from './constants'

// ============================================
// Status Formatters
// ============================================

export function formatConversationStatus(status: string): string {
  return CONVERSATION_STATUS_LABELS[status] || status
}

export function formatControlledBy(controlledBy: 'ai' | 'human'): string {
  return CONTROLLED_BY_LABELS[controlledBy]
}

export function formatMessageType(tipo: 'entrada' | 'saida'): string {
  return MESSAGE_TYPE_LABELS[tipo]
}

// ============================================
// Phone Number Formatters
// ============================================

export function formatPhone(phone: string): string {
  // Remove non-digits
  const cleaned = phone.replace(/\D/g, '')

  // Format Brazilian phone: +55 (11) 99999-9999
  if (cleaned.length === 13 && cleaned.startsWith('55')) {
    const ddd = cleaned.slice(2, 4)
    const firstPart = cleaned.slice(4, 9)
    const secondPart = cleaned.slice(9, 13)
    return '+55 (' + ddd + ') ' + firstPart + '-' + secondPart
  }

  // Format without country code: (11) 99999-9999
  if (cleaned.length === 11) {
    const ddd = cleaned.slice(0, 2)
    const firstPart = cleaned.slice(2, 7)
    const secondPart = cleaned.slice(7, 11)
    return '(' + ddd + ') ' + firstPart + '-' + secondPart
  }

  return phone
}

// ============================================
// Time Formatters
// ============================================

export function formatMessageTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()

  if (isToday) {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = date.toDateString() === yesterday.toDateString()

  if (isYesterday) {
    return 'Ontem ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelativeTime(timestamp: string | undefined): string {
  if (!timestamp) return '—'

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'agora'
  if (diffMins < 60) return diffMins + 'min'

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return diffHours + 'h'

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return 'ontem'
  if (diffDays < 7) return diffDays + 'd'

  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

// ============================================
// Message Preview Formatters
// ============================================

export function formatMessagePreview(content: string, maxLength: number = 50): string {
  if (content.length <= maxLength) return content
  return content.slice(0, maxLength) + '...'
}

// ============================================
// Client Name Formatters
// ============================================

export function formatClientName(nome: string): string {
  const parts = nome.split(' ')
  if (parts.length === 1) return parts[0] || ''
  return (parts[0] || '') + ' ' + (parts[parts.length - 1] || '')
}

export function getInitials(nome: string): string {
  const parts = nome.split(' ').filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return (parts[0]?.[0] || '?').toUpperCase()
  return ((parts[0]?.[0] || '') + (parts[parts.length - 1]?.[0] || '')).toUpperCase()
}
