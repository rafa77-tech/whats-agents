/**
 * Constantes para o módulo Chips
 * Sprint 43: UX & Operação Unificada
 */

import type {
  ChipStatus,
  TrustLevelExtended,
  WarmupPhase,
  ChipAlertSeverity,
  ChipAlertType,
} from './types'

// ============================================
// Status Constants
// ============================================

export const CHIP_STATUS_LABELS: Record<ChipStatus, string> = {
  provisioned: 'Provisionado',
  pending: 'Pendente',
  warming: 'Aquecendo',
  ready: 'Pronto',
  active: 'Ativo',
  degraded: 'Degradado',
  paused: 'Pausado',
  banned: 'Banido',
  cancelled: 'Cancelado',
  offline: 'Offline',
}

export const CHIP_STATUS_COLORS: Record<ChipStatus, string> = {
  provisioned: 'bg-status-neutral text-status-neutral-foreground',
  pending: 'bg-status-info text-status-info-foreground',
  warming: 'bg-status-warning text-status-warning-foreground',
  ready: 'bg-status-success text-status-success-foreground',
  active: 'bg-state-ai text-state-ai-foreground',
  degraded: 'bg-trust-laranja text-trust-laranja-foreground',
  paused: 'bg-status-neutral text-status-neutral-foreground/80',
  banned: 'bg-status-error text-status-error-foreground',
  cancelled: 'bg-status-error text-status-error-foreground/80',
  offline: 'bg-status-neutral/80 text-status-neutral-foreground/80',
}

// ============================================
// Trust Level Constants
// ============================================

export const TRUST_LEVEL_LABELS: Record<TrustLevelExtended, string> = {
  verde: 'Verde',
  amarelo: 'Amarelo',
  laranja: 'Laranja',
  vermelho: 'Vermelho',
  critico: 'Critico',
}

export const TRUST_LEVEL_COLORS: Record<TrustLevelExtended, string> = {
  verde: 'bg-status-success-solid',
  amarelo: 'bg-status-warning-solid',
  laranja: 'bg-trust-laranja-solid',
  vermelho: 'bg-status-error-solid',
  critico: 'bg-trust-critico',
}

export const TRUST_LEVEL_TEXT_COLORS: Record<TrustLevelExtended, string> = {
  verde: 'text-status-success-solid',
  amarelo: 'text-status-warning-solid',
  laranja: 'text-trust-laranja-foreground',
  vermelho: 'text-status-error-solid',
  critico: 'text-trust-critico',
}

// ============================================
// Warmup Phase Constants
// ============================================

export const WARMUP_PHASE_LABELS: Record<WarmupPhase, string> = {
  repouso: 'Repouso',
  setup: 'Setup',
  primeiros_contatos: 'Primeiros Contatos',
  expansao: 'Expansao',
  pre_operacao: 'Pre-Operacao',
  teste_graduacao: 'Teste Graduacao',
  operacao: 'Operacao',
}

export const WARMUP_PHASE_ORDER: WarmupPhase[] = [
  'repouso',
  'setup',
  'primeiros_contatos',
  'expansao',
  'pre_operacao',
  'teste_graduacao',
  'operacao',
]

// ============================================
// Alert Constants
// ============================================

export const ALERT_SEVERITY_LABELS: Record<ChipAlertSeverity, string> = {
  critico: 'Critico',
  alerta: 'Alerta',
  atencao: 'Atencao',
  info: 'Info',
}

export const ALERT_SEVERITY_COLORS: Record<ChipAlertSeverity, string> = {
  critico: 'bg-status-error text-status-error-foreground border-status-error-border',
  alerta: 'bg-trust-laranja text-trust-laranja-foreground border-trust-laranja',
  atencao: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
  info: 'bg-status-info text-status-info-foreground border-status-info-border',
}

export const ALERT_TYPE_LABELS: Record<ChipAlertType, string> = {
  TRUST_CAINDO: 'Trust Caindo',
  TAXA_BLOCK_ALTA: 'Taxa de Block Alta',
  ERROS_FREQUENTES: 'Erros Frequentes',
  DELIVERY_BAIXO: 'Delivery Baixo',
  RESPOSTA_BAIXA: 'Resposta Baixa',
  DESCONEXAO: 'Desconexao',
  LIMITE_PROXIMO: 'Limite Proximo',
  FASE_ESTAGNADA: 'Fase Estagnada',
  QUALIDADE_META: 'Qualidade Meta',
  COMPORTAMENTO_ANOMALO: 'Comportamento Anomalo',
}

// ============================================
// Pagination Constants
// ============================================

export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// ============================================
// Filter Constants
// ============================================

export const DEFAULT_FILTERS = {
  search: '',
  status: null,
  trustLevel: null,
  warmupPhase: null,
  hasAlert: null,
  sortBy: 'trust' as const,
  order: 'desc' as const,
}
