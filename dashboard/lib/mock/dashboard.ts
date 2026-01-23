/**
 * Mock data for Dashboard E2E tests
 *
 * Used when running E2E tests without a backend
 */

import type { ActivityType } from '@/types/dashboard'

export const mockActivity = {
  events: [
    {
      id: 'fechamento-1',
      type: 'fechamento' as ActivityType,
      message: 'fechou plantao com Dr. Silva',
      chipName: 'Julia',
      timestamp: '2026-01-23T11:30:00Z',
    },
    {
      id: 'campanha-1',
      type: 'campanha' as ActivityType,
      message: 'Campanha "Reativação Janeiro" enviou 45 mensagens',
      timestamp: '2026-01-23T10:00:00Z',
    },
    {
      id: 'chip-ready-1',
      type: 'chip' as ActivityType,
      message: 'graduou do warming (trust: 80)',
      chipName: 'julia-chip-003',
      timestamp: '2026-01-23T09:00:00Z',
    },
  ],
  hasMore: false,
}

export const mockAlerts = {
  alerts: [
    {
      id: 'alert-dash-1',
      type: 'warning' as const,
      title: 'Taxa de resposta baixa',
      message: 'A taxa de resposta está 15% abaixo da média',
      timestamp: '2026-01-23T08:00:00Z',
    },
  ],
  total: 1,
}

export const mockFunnel = {
  stages: [
    {
      stage: 'prospectados',
      count: 1250,
      rate: 100,
      previousCount: 1180,
    },
    {
      stage: 'responderam',
      count: 375,
      rate: 30,
      previousCount: 354,
    },
    {
      stage: 'interessados',
      count: 188,
      rate: 15,
      previousCount: 177,
    },
    {
      stage: 'negociando',
      count: 94,
      rate: 7.5,
      previousCount: 89,
    },
    {
      stage: 'fechados',
      count: 47,
      rate: 3.8,
      previousCount: 42,
    },
  ],
}

export const mockMetrics = {
  totalConversations: 1250,
  activeConversations: 89,
  closedToday: 12,
  avgResponseTime: 45,
  totalMessages: 8500,
  messagesPerDay: 285,
  previousTotalConversations: 1180,
  previousClosedToday: 10,
}

export const mockOperational = {
  status: 'operando' as const,
  rateLimitUsage: 45,
  rateLimitMax: 100,
  instances: [
    {
      name: 'julia-main',
      status: 'connected' as const,
      messagesLast24h: 150,
    },
    {
      name: 'julia-backup',
      status: 'connected' as const,
      messagesLast24h: 85,
    },
  ],
  lastUpdate: '2026-01-23T12:00:00Z',
}

export const mockQuality = {
  humanDetectionRate: 0.5,
  optOutRate: 2.1,
  handoffRate: 3.5,
  avgConversationLength: 8.2,
}

export const mockTrends = {
  conversations: [120, 135, 142, 138, 150, 145, 155],
  messages: [850, 920, 880, 950, 1020, 980, 1050],
  closings: [8, 10, 9, 12, 11, 14, 12],
  labels: ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'],
}

export const mockStatus = {
  juliaStatus: 'ativo' as const,
  chatwootStatus: 'conectado' as const,
  evolutionStatus: 'conectado' as const,
  databaseStatus: 'ok' as const,
}
