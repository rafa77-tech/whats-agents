/**
 * Constantes para o módulo Chips
 * Sprint 43: UX & Operação Unificada
 */

import type { ChipStatus, TrustLevelExtended, WarmupPhase, ChipAlertSeverity, ChipAlertType } from './types'

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
  provisioned: 'bg-gray-100 text-gray-800',
  pending: 'bg-blue-100 text-blue-800',
  warming: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-green-100 text-green-800',
  active: 'bg-emerald-100 text-emerald-800',
  degraded: 'bg-orange-100 text-orange-800',
  paused: 'bg-gray-100 text-gray-600',
  banned: 'bg-red-100 text-red-800',
  cancelled: 'bg-red-100 text-red-600',
  offline: 'bg-gray-200 text-gray-600',
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
  verde: 'bg-green-500',
  amarelo: 'bg-yellow-500',
  laranja: 'bg-orange-500',
  vermelho: 'bg-red-500',
  critico: 'bg-red-700',
}

export const TRUST_LEVEL_TEXT_COLORS: Record<TrustLevelExtended, string> = {
  verde: 'text-green-700',
  amarelo: 'text-yellow-700',
  laranja: 'text-orange-700',
  vermelho: 'text-red-700',
  critico: 'text-red-900',
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
  critico: 'bg-red-100 text-red-800 border-red-200',
  alerta: 'bg-orange-100 text-orange-800 border-orange-200',
  atencao: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  info: 'bg-blue-100 text-blue-800 border-blue-200',
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
