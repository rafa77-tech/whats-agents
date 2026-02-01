/**
 * Constantes para o modulo de Auditoria
 */

import {
  Power,
  Flag,
  User,
  Settings,
  RefreshCw,
  Megaphone,
  Play,
  Pause,
  type LucideIcon,
} from 'lucide-react'
import type { ActionOption } from './types'

// =============================================================================
// Paginacao
// =============================================================================

/**
 * Itens por pagina padrao
 */
export const DEFAULT_PER_PAGE = 50

/**
 * Limite maximo de export
 */
export const EXPORT_LIMIT = 10000

// =============================================================================
// Mapeamentos de acoes
// =============================================================================

/**
 * Icones por tipo de acao
 */
export const ACTION_ICONS: Record<string, LucideIcon> = {
  julia_toggle: Power,
  julia_pause: Power,
  feature_flag_update: Flag,
  rate_limit_update: Settings,
  manual_handoff: User,
  return_to_julia: RefreshCw,
  circuit_reset: RefreshCw,
  create_campaign: Megaphone,
  start_campaign: Play,
  pause_campaign: Pause,
}

/**
 * Labels por tipo de acao
 */
export const ACTION_LABELS: Record<string, string> = {
  julia_toggle: 'Toggle Julia',
  julia_pause: 'Pausar Julia',
  feature_flag_update: 'Atualizar Feature Flag',
  rate_limit_update: 'Atualizar Rate Limit',
  manual_handoff: 'Handoff Manual',
  return_to_julia: 'Retornar para Julia',
  circuit_reset: 'Reset Circuit Breaker',
  create_campaign: 'Criar Campanha',
  start_campaign: 'Iniciar Campanha',
  pause_campaign: 'Pausar Campanha',
}

/**
 * Opcoes de acao para filtro
 */
export const ACTION_OPTIONS: ActionOption[] = [
  { value: 'julia_toggle', label: 'Toggle Julia' },
  { value: 'julia_pause', label: 'Pausar Julia' },
  { value: 'feature_flag_update', label: 'Feature Flag' },
  { value: 'rate_limit_update', label: 'Rate Limit' },
  { value: 'manual_handoff', label: 'Handoff Manual' },
  { value: 'return_to_julia', label: 'Retornar Julia' },
  { value: 'circuit_reset', label: 'Reset Circuit' },
  { value: 'create_campaign', label: 'Criar Campanha' },
  { value: 'start_campaign', label: 'Iniciar Campanha' },
  { value: 'pause_campaign', label: 'Pausar Campanha' },
]

// =============================================================================
// Endpoints da API
// =============================================================================

/**
 * Endpoints utilizados pelo modulo de auditoria
 */
export const API_ENDPOINTS = {
  logs: '/api/auditoria',
  export: '/api/auditoria/export',
} as const

// =============================================================================
// Valores default
// =============================================================================

/**
 * Filtros default
 */
export const DEFAULT_FILTERS = {
  action: undefined,
  actor_email: undefined,
  from_date: undefined,
  to_date: undefined,
} as const
