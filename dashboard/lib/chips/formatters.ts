/**
 * Formatadores para o módulo Chips
 * Sprint 43: UX & Operação Unificada
 */

import type { ChipStatus, TrustLevelExtended, WarmupPhase } from './types'
import {
  CHIP_STATUS_LABELS,
  TRUST_LEVEL_LABELS,
  WARMUP_PHASE_LABELS,
  WARMUP_PHASE_ORDER,
} from './constants'

// ============================================
// Status Formatters
// ============================================

export function formatChipStatus(status: ChipStatus): string {
  return CHIP_STATUS_LABELS[status] || status
}

export function formatTrustLevel(level: TrustLevelExtended): string {
  return TRUST_LEVEL_LABELS[level] || level
}

export function formatWarmupPhase(phase: WarmupPhase | null): string {
  if (!phase) return '—'
  return WARMUP_PHASE_LABELS[phase] || phase
}

// ============================================
// Trust Score Formatters
// ============================================

export function formatTrustScore(score: number): string {
  return score.toFixed(0)
}

export function getTrustLevelFromScore(score: number): TrustLevelExtended {
  if (score >= 80) return 'verde'
  if (score >= 60) return 'amarelo'
  if (score >= 40) return 'laranja'
  if (score >= 20) return 'vermelho'
  return 'critico'
}

// ============================================
// Warmup Progress Formatters
// ============================================

export function getWarmupProgress(phase: WarmupPhase | null): number {
  if (!phase) return 0
  const index = WARMUP_PHASE_ORDER.indexOf(phase)
  if (index === -1) return 0
  return Math.round(((index + 1) / WARMUP_PHASE_ORDER.length) * 100)
}

export function formatWarmupDay(day: number | undefined): string {
  if (day === undefined || day === null) return '—'
  return 'Dia ' + String(day)
}

// ============================================
// Rate Formatters
// ============================================

export function formatResponseRate(rate: number): string {
  return rate.toFixed(1) + '%'
}

export function formatDeliveryRate(rate: number): string {
  return rate.toFixed(1) + '%'
}

export function formatBlockRate(rate: number): string {
  return rate.toFixed(1) + '%'
}

// ============================================
// Message Count Formatters
// ============================================

export function formatMessageCount(current: number, limit: number): string {
  return current + '/' + limit
}

export function formatMessageUsagePercent(current: number, limit: number): number {
  if (limit === 0) return 0
  return Math.min((current / limit) * 100, 100)
}

// ============================================
// Phone Number Formatters
// ============================================

export function formatPhoneNumber(phone: string): string {
  // Format Brazilian phone: +55 (11) 99999-9999
  const cleaned = phone.replace(/\D/g, '')

  if (cleaned.length === 13 && cleaned.startsWith('55')) {
    const ddd = cleaned.slice(2, 4)
    const firstPart = cleaned.slice(4, 9)
    const secondPart = cleaned.slice(9, 13)
    return '+55 (' + ddd + ') ' + firstPart + '-' + secondPart
  }

  if (cleaned.length === 11) {
    const ddd = cleaned.slice(0, 2)
    const firstPart = cleaned.slice(2, 7)
    const secondPart = cleaned.slice(7, 11)
    return '(' + ddd + ') ' + firstPart + '-' + secondPart
  }

  return phone
}

// ============================================
// Timestamp Formatters
// ============================================

export function formatChipTimestamp(timestamp: string | null): string {
  if (!timestamp) return 'Nunca'

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Agora'
  if (diffMins < 60) return diffMins + 'min atrás'

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return diffHours + 'h atrás'

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return diffDays + 'd atrás'

  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

export function formatChipDate(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}
