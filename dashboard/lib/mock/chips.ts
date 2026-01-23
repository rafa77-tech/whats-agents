/**
 * Mock data for Chips E2E tests
 *
 * Used when running E2E tests without a backend
 */

import type {
  PoolStatus,
  ChipsListResponse,
  ChipListItem,
  ChipFullDetail,
  ChipMetrics,
  ChipTrustHistory,
  PoolHealthStatus,
  ChipAlertsListResponse,
  ScheduledActivity,
  SchedulerStats,
  PoolConfig,
} from '@/types/chips'

export const mockChip: ChipListItem = {
  id: 'chip-mock-1',
  telefone: '+5511999990001',
  status: 'active',
  trustScore: 85,
  trustLevel: 'verde',
  warmupPhase: 'operacao',
  messagesToday: 45,
  dailyLimit: 100,
  responseRate: 32.5,
  errorsLast24h: 2,
  hasActiveAlert: false,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2026-01-23T12:00:00Z',
}

export const mockChips: ChipListItem[] = [
  mockChip,
  {
    ...mockChip,
    id: 'chip-mock-2',
    telefone: '+5511999990002',
    status: 'warming',
    trustScore: 65,
    trustLevel: 'amarelo',
    warmupPhase: 'expansao',
    messagesToday: 20,
    dailyLimit: 50,
    warmingDay: 15,
  },
  {
    ...mockChip,
    id: 'chip-mock-3',
    telefone: '+5511999990003',
    status: 'ready',
    trustScore: 78,
    trustLevel: 'verde',
    warmupPhase: null,
    messagesToday: 0,
    dailyLimit: 100,
  },
  {
    ...mockChip,
    id: 'chip-mock-4',
    telefone: '+5511999990004',
    status: 'paused',
    trustScore: 40,
    trustLevel: 'laranja',
    warmupPhase: null,
    hasActiveAlert: true,
    alertMessage: 'Trust score baixo',
  },
  {
    ...mockChip,
    id: 'chip-mock-5',
    telefone: '+5511999990005',
    status: 'degraded',
    trustScore: 25,
    trustLevel: 'vermelho',
    warmupPhase: null,
    errorsLast24h: 15,
    hasActiveAlert: true,
    alertMessage: 'Muitos erros nas últimas 24h',
  },
]

export const mockPoolStatus: PoolStatus = {
  total: 5,
  byStatus: {
    provisioned: 0,
    pending: 0,
    warming: 1,
    ready: 1,
    active: 1,
    degraded: 1,
    paused: 1,
    banned: 0,
    cancelled: 0,
    offline: 0,
  },
  byTrustLevel: {
    verde: 2,
    amarelo: 1,
    laranja: 1,
    vermelho: 1,
    critico: 0,
  },
  avgTrustScore: 58.6,
  totalMessagesToday: 65,
  totalDailyCapacity: 400,
  activeAlerts: 2,
  criticalAlerts: 1,
}

export const mockChipsListResponse: ChipsListResponse = {
  chips: mockChips,
  total: 5,
  page: 1,
  pageSize: 10,
  hasMore: false,
}

export const mockChipDetail: ChipFullDetail = {
  ...mockChip,
  ddd: '11',
  region: 'São Paulo',
  instanceName: 'julia-chip-001',
  deliveryRate: 95.5,
  blockRate: 2.1,
  lastActivityAt: '2026-01-23T11:45:00Z',
  totalMessagesSent: 1250,
  totalConversations: 89,
  totalBidirectional: 45,
  groupsJoined: 3,
  mediaTypesSent: ['text', 'image', 'audio'],
}

export const mockChipMetrics: ChipMetrics = {
  period: '24h',
  messagesSent: 45,
  messagesReceived: 15,
  responseRate: 32.5,
  deliveryRate: 95.5,
  errorCount: 2,
  avgResponseTime: 120,
  previousMessagesSent: 42,
  previousResponseRate: 30.0,
  previousErrorCount: 3,
}

export const mockTrustHistory: ChipTrustHistory = {
  history: [
    { timestamp: '2026-01-20T00:00:00Z', score: 75, level: 'verde' },
    { timestamp: '2026-01-21T00:00:00Z', score: 78, level: 'verde' },
    { timestamp: '2026-01-22T00:00:00Z', score: 82, level: 'verde' },
    { timestamp: '2026-01-23T00:00:00Z', score: 85, level: 'verde' },
  ],
  events: [
    {
      id: 'event-1',
      timestamp: '2026-01-22T10:00:00Z',
      type: 'increase',
      description: 'Boa taxa de resposta mantida',
      scoreBefore: 78,
      scoreAfter: 82,
    },
  ],
}

export const mockPoolHealth: PoolHealthStatus = {
  status: 'attention',
  score: 72,
  issues: [
    {
      id: 'issue-1',
      type: 'high_errors',
      severity: 'warning',
      message: '1 chip com taxa de erros elevada',
      affectedChips: 1,
      recommendation: 'Considere pausar o chip temporariamente',
    },
  ],
  lastUpdated: '2026-01-23T12:00:00Z',
}

export const mockAlertsResponse: ChipAlertsListResponse = {
  alerts: [
    {
      id: 'alert-1',
      chipId: 'chip-mock-4',
      chipTelefone: '+5511999990004',
      type: 'TRUST_CAINDO',
      severity: 'alerta',
      title: 'Trust Score em Queda',
      message: 'O trust score caiu 20 pontos nas últimas 48h',
      recommendation: 'Reduzir volume de mensagens',
      createdAt: '2026-01-23T08:00:00Z',
    },
    {
      id: 'alert-2',
      chipId: 'chip-mock-5',
      chipTelefone: '+5511999990005',
      type: 'ERROS_FREQUENTES',
      severity: 'critico',
      title: 'Erros Frequentes',
      message: '15 erros nas últimas 24h',
      recommendation: 'Pausar chip e investigar',
      createdAt: '2026-01-23T10:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  pageSize: 10,
  hasMore: false,
  countBySeverity: {
    critico: 1,
    alerta: 1,
    atencao: 0,
    info: 0,
  },
}

export const mockScheduledActivities: ScheduledActivity[] = [
  {
    id: 'activity-1',
    chipId: 'chip-mock-1',
    chipTelefone: '+5511999990001',
    type: 'CONVERSA_PAR',
    scheduledAt: '2026-01-23T14:00:00Z',
    status: 'planejada',
  },
  {
    id: 'activity-2',
    chipId: 'chip-mock-2',
    chipTelefone: '+5511999990002',
    type: 'MARCAR_LIDO',
    scheduledAt: '2026-01-23T14:30:00Z',
    status: 'planejada',
  },
]

export const mockSchedulerStats: SchedulerStats = {
  date: '2026-01-23',
  totalPlanned: 25,
  totalExecuted: 18,
  totalFailed: 2,
  totalCancelled: 1,
  byType: {
    CONVERSA_PAR: { planned: 10, executed: 8, failed: 1 },
    MARCAR_LIDO: { planned: 8, executed: 6, failed: 0 },
    ENTRAR_GRUPO: { planned: 2, executed: 1, failed: 1 },
    ENVIAR_MIDIA: { planned: 3, executed: 2, failed: 0 },
    MENSAGEM_GRUPO: { planned: 2, executed: 1, failed: 0 },
    ATUALIZAR_PERFIL: { planned: 0, executed: 0, failed: 0 },
  },
}

export const mockPoolConfig: PoolConfig = {
  maxChipsActive: 10,
  maxChipsWarming: 5,
  minChipsReady: 3,
  maxMsgsPerHour: 20,
  maxMsgsPerDay: 100,
  minIntervalSeconds: 45,
  autoPromoteEnabled: true,
  autoDemoteEnabled: true,
  minTrustForPromotion: 75,
  alertThresholds: {
    trustDropWarning: 10,
    trustDropCritical: 20,
    errorRateWarning: 5,
    errorRateCritical: 10,
  },
  operatingHours: {
    start: '08:00',
    end: '20:00',
  },
  operatingDays: [1, 2, 3, 4, 5],
}
