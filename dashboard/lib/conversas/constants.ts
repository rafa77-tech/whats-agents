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
  julia_ativa: 'border-l-status-success-solid',
  aguardando: 'border-l-status-warning-solid',
  encerradas: 'border-l-muted-foreground',
}

export const SENTIMENTO_COLORS: Record<string, string> = {
  positivo: 'bg-status-success-solid',
  neutro: 'bg-status-neutral-solid',
  negativo: 'bg-destructive',
}

export function getSentimentColor(score: number | undefined | null): string {
  if (score == null) return 'bg-status-neutral-solid'
  if (score >= 2) return 'bg-status-success-solid'
  if (score <= -2) return 'bg-destructive'
  return 'bg-status-neutral-solid'
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
  novo: 'bg-status-info text-status-info-foreground',
  interessado: 'bg-accent/20 text-accent',
  prospectado: 'bg-status-info/70 text-status-info-foreground',
  negociando: 'bg-status-warning text-status-warning-foreground',
  ativo: 'bg-status-success text-status-success-foreground',
  inativo: 'bg-status-neutral text-status-neutral-foreground',
  perdido: 'bg-status-error text-status-error-foreground',
}
