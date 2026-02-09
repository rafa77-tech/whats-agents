/**
 * Constantes para o modulo Conversas
 * Sprint 43: UX & Operacao Unificada
 * Sprint 54: Supervision Dashboard
 */

// ============================================
// Status Constants
// ============================================

export const CONVERSATION_STATUS_LABELS: Record<string, string> = {
  ativa: 'Ativa',
  pausada: 'Pausada',
  encerrada: 'Encerrada',
  arquivada: 'Arquivada',
}

export const CONVERSATION_STATUS_COLORS: Record<string, string> = {
  ativa: 'bg-status-success text-status-success-foreground',
  pausada: 'bg-status-warning text-status-warning-foreground',
  encerrada: 'bg-status-neutral text-status-neutral-foreground',
  arquivada: 'bg-status-neutral/50 text-status-neutral-foreground/70',
}

// ============================================
// Control Constants
// ============================================

export const CONTROLLED_BY_LABELS = {
  ai: 'Julia',
  human: 'Humano',
} as const

export const CONTROLLED_BY_COLORS = {
  ai: 'bg-status-info text-status-info-foreground',
  human: 'bg-accent/20 text-accent',
} as const

// ============================================
// Message Type Constants
// ============================================

export const MESSAGE_TYPE_LABELS = {
  entrada: 'Recebida',
  saida: 'Enviada',
} as const

// ============================================
// Filter Constants
// ============================================

export const DEFAULT_FILTERS = {
  status: undefined,
  controlled_by: undefined,
  search: '',
  chip_id: undefined,
} as const

// ============================================
// Pagination Constants
// ============================================

export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// ============================================
// Supervision Tab Constants (Sprint 54)
// ============================================

export const SUPERVISION_TABS = [
  { id: 'atencao', label: 'Atencao', icon: 'AlertTriangle' },
  { id: 'julia_ativa', label: 'Julia Ativa', icon: 'Bot' },
  { id: 'aguardando', label: 'Aguardando', icon: 'Clock' },
  { id: 'encerradas', label: 'Encerradas', icon: 'CheckCircle' },
] as const

export const URGENCY_COLORS: Record<string, string> = {
  atencao: 'border-l-destructive',
  julia_ativa: 'border-l-emerald-500',
  aguardando: 'border-l-amber-400',
  encerradas: 'border-l-muted-foreground',
}

export const SENTIMENTO_COLORS: Record<string, string> = {
  positivo: 'bg-emerald-500',
  neutro: 'bg-slate-400',
  negativo: 'bg-destructive',
}

export function getSentimentColor(score: number | undefined | null): string {
  if (score == null) return 'bg-slate-400'
  if (score >= 2) return 'bg-emerald-500'
  if (score <= -2) return 'bg-destructive'
  return 'bg-slate-400'
}

export function getSentimentLabel(score: number | undefined | null): string {
  if (score == null) return 'Neutro'
  if (score >= 2) return 'Positivo'
  if (score <= -2) return 'Negativo'
  return 'Neutro'
}

// ============================================
// Stage Constants (Sprint 54)
// ============================================

export const STAGE_LABELS: Record<string, string> = {
  novo: 'Novo',
  interessado: 'Interessado',
  prospectado: 'Prospectado',
  negociando: 'Negociando',
  ativo: 'Ativo',
  inativo: 'Inativo',
  perdido: 'Perdido',
}

export const STAGE_COLORS: Record<string, string> = {
  novo: 'bg-blue-100 text-blue-700',
  interessado: 'bg-purple-100 text-purple-700',
  prospectado: 'bg-indigo-100 text-indigo-700',
  negociando: 'bg-amber-100 text-amber-700',
  ativo: 'bg-emerald-100 text-emerald-700',
  inativo: 'bg-slate-100 text-slate-600',
  perdido: 'bg-red-100 text-red-700',
}
