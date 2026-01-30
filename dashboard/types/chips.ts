/**
 * Chips Types - Sprint 36
 *
 * Tipos para o módulo de gerenciamento de chips.
 * Complementa os tipos base em dashboard.ts
 */

// Re-export base types
export type {
  ChipStatus,
  TrustLevel,
  ChipSummary,
  ChipDetail,
  ChipPoolMetrics,
  ChipStatusCount,
  TrustDistribution,
  ChipPoolAggregatedMetrics,
  ChipPoolOverviewData,
} from './dashboard'

// ============================================================================
// Extended Chip Types
// ============================================================================

export type WarmupPhase =
  | 'repouso'
  | 'setup'
  | 'primeiros_contatos'
  | 'expansao'
  | 'pre_operacao'
  | 'teste_graduacao'
  | 'operacao'

export type TrustLevelExtended = 'verde' | 'amarelo' | 'laranja' | 'vermelho' | 'critico'

export interface ChipListItem {
  id: string
  telefone: string
  status: import('./dashboard').ChipStatus
  trustScore: number
  trustLevel: TrustLevelExtended
  warmupPhase: WarmupPhase | null
  messagesToday: number
  dailyLimit: number
  responseRate: number
  errorsLast24h: number
  hasActiveAlert: boolean
  alertMessage?: string
  warmingDay?: number
  createdAt: string
  updatedAt: string
}

export interface ChipFullDetail extends ChipListItem {
  ddd: string
  region: string
  instanceName: string
  deliveryRate: number
  blockRate: number
  lastActivityAt: string | null
  totalMessagesSent: number
  totalConversations: number
  totalBidirectional: number
  groupsJoined: number
  mediaTypesSent: string[]
}

// ============================================================================
// Pool Status Types
// ============================================================================

export interface PoolStatus {
  total: number
  byStatus: Record<import('./dashboard').ChipStatus, number>
  byTrustLevel: Record<TrustLevelExtended, number>
  avgTrustScore: number
  totalMessagesSent: number
  previousMessagesSent: number
  totalResponses: number
  previousResponses: number
  responseRate: number
  previousResponseRate: number
  totalDailyCapacity: number
  activeAlerts: number
  criticalAlerts: number
}

export interface PoolHealthStatus {
  status: 'healthy' | 'attention' | 'warning' | 'critical'
  score: number
  issues: PoolHealthIssue[]
  lastUpdated: string
}

export interface PoolHealthIssue {
  id: string
  type: 'trust_dropping' | 'high_errors' | 'low_capacity' | 'stale_chips' | 'ban_risk'
  severity: 'info' | 'warning' | 'critical'
  message: string
  affectedChips: number
  recommendation?: string
}

// ============================================================================
// List/Pagination Types
// ============================================================================

export interface ChipsListParams {
  page?: number
  pageSize?: number
  status?: import('./dashboard').ChipStatus | import('./dashboard').ChipStatus[]
  trustLevel?: TrustLevelExtended | TrustLevelExtended[]
  warmupPhase?: WarmupPhase | WarmupPhase[]
  hasAlert?: boolean
  search?: string
  sortBy?: 'trust' | 'status' | 'messages' | 'errors' | 'createdAt' | 'responseRate'
  order?: 'asc' | 'desc'
}

export interface ChipsListResponse {
  chips: ChipListItem[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

// ============================================================================
// Metrics Types
// ============================================================================

export interface ChipMetrics {
  period: '1h' | '6h' | '24h' | '7d' | '30d'
  messagesSent: number
  messagesReceived: number
  responseRate: number
  deliveryRate: number
  errorCount: number
  avgResponseTime: number
  // Comparativo
  previousMessagesSent: number
  previousResponseRate: number
  previousErrorCount: number
}

export interface ChipMetricsHistory {
  timestamps: string[]
  messagesSent: number[]
  responseRate: number[]
  errorCount: number[]
}

// ============================================================================
// Trust History Types
// ============================================================================

export interface TrustHistoryPoint {
  timestamp: string
  score: number
  level: TrustLevelExtended
}

export interface TrustEvent {
  id: string
  timestamp: string
  type: 'increase' | 'decrease' | 'phase_change' | 'alert'
  description: string
  scoreBefore: number
  scoreAfter: number
}

export interface ChipTrustHistory {
  history: TrustHistoryPoint[]
  events: TrustEvent[]
}

// ============================================================================
// Interactions Types
// ============================================================================

export type InteractionType =
  | 'conversa_individual'
  | 'mensagem_grupo'
  | 'entrada_grupo'
  | 'midia_enviada'
  | 'erro'
  | 'warmup_par'

export interface ChipInteraction {
  id: string
  type: InteractionType
  timestamp: string
  description: string
  success: boolean
  metadata?: Record<string, unknown>
}

export interface ChipInteractionsResponse {
  interactions: ChipInteraction[]
  total: number
  hasMore: boolean
}

// ============================================================================
// Alert Types
// ============================================================================

export type ChipAlertType =
  | 'TRUST_CAINDO'
  | 'TAXA_BLOCK_ALTA'
  | 'ERROS_FREQUENTES'
  | 'DELIVERY_BAIXO'
  | 'RESPOSTA_BAIXA'
  | 'DESCONEXAO'
  | 'LIMITE_PROXIMO'
  | 'FASE_ESTAGNADA'
  | 'QUALIDADE_META'
  | 'COMPORTAMENTO_ANOMALO'

export type ChipAlertSeverity = 'critico' | 'alerta' | 'atencao' | 'info'

export interface ChipAlert {
  id: string
  chipId: string
  chipTelefone: string
  type: ChipAlertType
  severity: ChipAlertSeverity
  title: string
  message: string
  recommendation?: string
  createdAt: string
  resolvedAt?: string
  resolvedBy?: string
  resolutionNotes?: string
}

export interface ChipAlertsListParams {
  severity?: ChipAlertSeverity | ChipAlertSeverity[]
  type?: ChipAlertType | ChipAlertType[]
  chipId?: string
  resolved?: boolean
  page?: number
  pageSize?: number
}

export interface ChipAlertsListResponse {
  alerts: ChipAlert[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
  countBySeverity: Record<ChipAlertSeverity, number>
}

// ============================================================================
// Scheduler Types
// ============================================================================

export type ScheduledActivityType =
  | 'CONVERSA_PAR'
  | 'MARCAR_LIDO'
  | 'ENTRAR_GRUPO'
  | 'ENVIAR_MIDIA'
  | 'MENSAGEM_GRUPO'
  | 'ATUALIZAR_PERFIL'

export type ActivityStatus = 'planejada' | 'executada' | 'falhou' | 'cancelada'

export interface ScheduledActivity {
  id: string
  chipId: string
  chipTelefone: string
  type: ScheduledActivityType
  scheduledAt: string
  executedAt?: string
  status: ActivityStatus
  errorMessage?: string
}

export interface SchedulerStats {
  date: string
  totalPlanned: number
  totalExecuted: number
  totalFailed: number
  totalCancelled: number
  byType: Record<
    ScheduledActivityType,
    {
      planned: number
      executed: number
      failed: number
    }
  >
}

// ============================================================================
// Config Types
// ============================================================================

export interface PoolConfig {
  // Limites gerais
  maxChipsActive: number
  maxChipsWarming: number
  minChipsReady: number

  // Limites de mensagem
  maxMsgsPerHour: number
  maxMsgsPerDay: number
  minIntervalSeconds: number

  // Warmup
  autoPromoteEnabled: boolean
  autoDemoteEnabled: boolean
  minTrustForPromotion: number

  // Alertas
  alertThresholds: {
    trustDropWarning: number
    trustDropCritical: number
    errorRateWarning: number
    errorRateCritical: number
  }

  // Horários
  operatingHours: {
    start: string
    end: string
  }
  operatingDays: number[]
}

// ============================================================================
// Action Response Types
// ============================================================================

export interface ChipActionResponse {
  success: boolean
  message?: string
  chip?: ChipListItem
}

// ============================================================================
// Instance Management Types (Sprint 40)
// ============================================================================

export interface CreateInstanceRequest {
  telefone: string
  instanceName?: string
}

export interface CreateInstanceResponse {
  success: boolean
  instanceName: string
  chipId: string
}

export interface QRCodeResponse {
  qrCode: string | null
  state: 'open' | 'close' | 'connecting'
  pairingCode?: string | null
}

export interface ConnectionStateResponse {
  state: 'open' | 'close' | 'connecting'
  connected: boolean
}

export type InstanceConnectionState = 'open' | 'close' | 'connecting'
