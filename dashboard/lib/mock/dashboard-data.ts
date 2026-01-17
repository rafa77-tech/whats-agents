/**
 * Mock data for dashboard components
 * Sprint 33 - Dashboard Performance Julia
 *
 * This file contains mock data used during development.
 * Will be replaced by real API calls in E08.
 */

import {
  type MetricData,
  type QualityMetricData,
  type OperationalStatusData,
  type ChipPoolOverviewData,
  type ChipDetail,
  type FunnelDataVisual,
  type TrendsData,
  type AlertsData,
  type ActivityFeedData,
} from "@/types/dashboard";

// ============================================================================
// E03 - Metrics vs Meta
// ============================================================================

export const mockMetricsVsMeta: MetricData[] = [
  {
    label: "Taxa de Resposta",
    value: 32,
    unit: "percent",
    meta: 30,
    previousValue: 28,
    metaOperator: "gt",
  },
  {
    label: "Taxa de Conversao",
    value: 18,
    unit: "percent",
    meta: 25,
    previousValue: 20,
    metaOperator: "gt",
  },
  {
    label: "Fechamentos/Semana",
    value: 18,
    unit: "number",
    meta: 15,
    previousValue: 15,
    metaOperator: "gt",
  },
];

// ============================================================================
// E04 - Quality Metrics
// ============================================================================

export const mockQualityMetrics: QualityMetricData[] = [
  {
    label: "Deteccao como Bot",
    value: 0.4,
    unit: "percent",
    threshold: { good: 1, warning: 3 },
    operator: "lt",
    previousValue: 0.6,
    tooltip:
      "Porcentagem de conversas onde o medico detectou que estava falando com um bot",
  },
  {
    label: "Latencia Media",
    value: 24,
    unit: "seconds",
    threshold: { good: 30, warning: 60 },
    operator: "lt",
    previousValue: 28,
    tooltip: "Tempo medio que Julia leva para responder uma mensagem",
  },
  {
    label: "Taxa de Handoff",
    value: 3.2,
    unit: "percent",
    threshold: { good: 5, warning: 10 },
    operator: "lt",
    previousValue: 4.1,
    tooltip: "Porcentagem de conversas transferidas para atendimento humano",
  },
];

// ============================================================================
// E05 - Operational Status
// ============================================================================

export const mockOperationalStatus: OperationalStatusData = {
  rateLimitHour: {
    current: 8,
    max: 20,
    label: "Rate Limit Hora",
  },
  rateLimitDay: {
    current: 78,
    max: 100,
    label: "Rate Limit Dia",
  },
  queueSize: 3,
  llmUsage: {
    haiku: 82,
    sonnet: 18,
  },
  instances: [
    { name: "Julia-01", status: "online", messagesToday: 47 },
    { name: "Julia-02", status: "online", messagesToday: 52 },
    { name: "Julia-03", status: "offline", messagesToday: 0 },
  ],
};

// ============================================================================
// E06 - Chip Pool Overview
// ============================================================================

export const mockChipPoolOverview: ChipPoolOverviewData = {
  statusCounts: [
    { status: "active", count: 5 },
    { status: "ready", count: 3 },
    { status: "warming", count: 4 },
    { status: "degraded", count: 1 },
  ],
  trustDistribution: [
    { level: "verde", count: 6, percentage: 46 },
    { level: "amarelo", count: 2, percentage: 15 },
    { level: "laranja", count: 1, percentage: 8 },
    { level: "vermelho", count: 0, percentage: 0 },
  ],
  metrics: {
    totalMessagesSent: 2847,
    avgResponseRate: 94.2,
    avgBlockRate: 1.8,
    totalErrors: 12,
    previousMessagesSent: 2475,
    previousResponseRate: 92.1,
    previousBlockRate: 2.3,
    previousErrors: 16,
  },
};

// ============================================================================
// E07 - Chip List Detailed
// ============================================================================

export const mockChipsList: ChipDetail[] = [
  {
    id: "1",
    name: "Julia-01",
    telefone: "+5511999990001",
    status: "active",
    trustScore: 92,
    trustLevel: "verde",
    messagesToday: 47,
    dailyLimit: 100,
    responseRate: 96.2,
    errorsLast24h: 0,
    hasActiveAlert: false,
  },
  {
    id: "2",
    name: "Julia-02",
    telefone: "+5511999990002",
    status: "active",
    trustScore: 88,
    trustLevel: "verde",
    messagesToday: 52,
    dailyLimit: 100,
    responseRate: 94.8,
    errorsLast24h: 1,
    hasActiveAlert: false,
  },
  {
    id: "3",
    name: "Julia-03",
    telefone: "+5511999990003",
    status: "ready",
    trustScore: 85,
    trustLevel: "verde",
    messagesToday: 0,
    dailyLimit: 100,
    responseRate: 0,
    errorsLast24h: 0,
    hasActiveAlert: false,
  },
  {
    id: "4",
    name: "Julia-04",
    telefone: "+5511999990004",
    status: "warming",
    trustScore: 72,
    trustLevel: "amarelo",
    messagesToday: 15,
    dailyLimit: 30,
    responseRate: 91.0,
    errorsLast24h: 0,
    hasActiveAlert: false,
    warmingDay: 14,
  },
  {
    id: "5",
    name: "Julia-05",
    telefone: "+5511999990005",
    status: "degraded",
    trustScore: 48,
    trustLevel: "laranja",
    messagesToday: 8,
    dailyLimit: 30,
    responseRate: 78.5,
    errorsLast24h: 3,
    hasActiveAlert: true,
    alertMessage: "Trust baixo",
  },
];

// ============================================================================
// E10 - Conversion Funnel
// ============================================================================

export const mockFunnelData: FunnelDataVisual = {
  stages: [
    {
      id: "enviadas",
      label: "Enviadas",
      count: 320,
      previousCount: 286,
      percentage: 100,
    },
    {
      id: "entregues",
      label: "Entregues",
      count: 312,
      previousCount: 281,
      percentage: 97.5,
    },
    {
      id: "respostas",
      label: "Respostas",
      count: 102,
      previousCount: 86,
      percentage: 31.9,
    },
    {
      id: "interesse",
      label: "Interesse",
      count: 48,
      previousCount: 44,
      percentage: 15,
    },
    {
      id: "fechadas",
      label: "Fechadas",
      count: 18,
      previousCount: 15,
      percentage: 5.6,
    },
  ],
  period: "7 dias",
};

// ============================================================================
// E12 - Trends Sparklines
// ============================================================================

export const mockTrendsData: TrendsData = {
  metrics: [
    {
      id: "responseRate",
      label: "Taxa de Resposta",
      data: [
        { date: "2025-01-10", value: 28 },
        { date: "2025-01-11", value: 29 },
        { date: "2025-01-12", value: 27 },
        { date: "2025-01-13", value: 30 },
        { date: "2025-01-14", value: 31 },
        { date: "2025-01-15", value: 30 },
        { date: "2025-01-16", value: 32 },
      ],
      currentValue: 32,
      unit: "%",
      trend: "up",
      trendIsGood: true,
    },
    {
      id: "latency",
      label: "Latencia Media",
      data: [
        { date: "2025-01-10", value: 30 },
        { date: "2025-01-11", value: 28 },
        { date: "2025-01-12", value: 32 },
        { date: "2025-01-13", value: 26 },
        { date: "2025-01-14", value: 25 },
        { date: "2025-01-15", value: 24 },
        { date: "2025-01-16", value: 24 },
      ],
      currentValue: 24,
      unit: "s",
      trend: "down",
      trendIsGood: true,
    },
    {
      id: "botDetection",
      label: "Deteccao Bot",
      data: [
        { date: "2025-01-10", value: 0.8 },
        { date: "2025-01-11", value: 0.6 },
        { date: "2025-01-12", value: 0.7 },
        { date: "2025-01-13", value: 0.5 },
        { date: "2025-01-14", value: 0.5 },
        { date: "2025-01-15", value: 0.4 },
        { date: "2025-01-16", value: 0.4 },
      ],
      currentValue: 0.4,
      unit: "%",
      trend: "down",
      trendIsGood: true,
    },
    {
      id: "trustScore",
      label: "Trust Score Medio",
      data: [
        { date: "2025-01-10", value: 78 },
        { date: "2025-01-11", value: 79 },
        { date: "2025-01-12", value: 78 },
        { date: "2025-01-13", value: 80 },
        { date: "2025-01-14", value: 81 },
        { date: "2025-01-15", value: 82 },
        { date: "2025-01-16", value: 82 },
      ],
      currentValue: 82,
      unit: "",
      trend: "up",
      trendIsGood: true,
    },
  ],
  period: "7d",
};

// ============================================================================
// E13 - Alerts
// ============================================================================

export const mockAlertsData: AlertsData = {
  alerts: [
    {
      id: "alert-1",
      severity: "critical",
      category: "julia",
      title: "Dr. Joao - aguardando atendimento",
      message: "Medico solicitou falar com humano ha 2 horas",
      createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      actionLabel: "Ver conversa",
      actionUrl: "#",
    },
    {
      id: "alert-2",
      severity: "critical",
      category: "chip",
      title: "Julia-05 - Trust critico",
      message: "Trust score caiu para 48 (-15 pts em 24h)",
      createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      actionLabel: "Ver chip",
      actionUrl: "#",
    },
    {
      id: "alert-3",
      severity: "warning",
      category: "operational",
      title: "Rate limit hora em 85%",
      message: "Reseta em 12 minutos",
      createdAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    },
    {
      id: "alert-4",
      severity: "warning",
      category: "vaga",
      title: "5 vagas expirando em 24h",
      message: "Sem medico confirmado",
      createdAt: new Date().toISOString(),
      actionLabel: "Ver vagas",
      actionUrl: "#",
    },
  ],
  totalCritical: 2,
  totalWarning: 2,
};

// ============================================================================
// E14 - Activity Feed
// ============================================================================

export const mockActivityData: ActivityFeedData = {
  events: [
    {
      id: "event-1",
      type: "fechamento",
      message: "fechou plantao com Dr. Carlos (R$ 2.800)",
      chipName: "Julia-01",
      timestamp: new Date(Date.now() - 28 * 60 * 1000).toISOString(),
    },
    {
      id: "event-2",
      type: "handoff",
      message: "handoff: Dra. Maria pediu humano",
      chipName: "Julia-02",
      timestamp: new Date(Date.now() - 32 * 60 * 1000).toISOString(),
    },
    {
      id: "event-3",
      type: "campanha",
      message: 'Campanha "Reativacao Janeiro" enviou 15 mensagens',
      timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    },
    {
      id: "event-4",
      type: "resposta",
      message: "Dr. Pedro respondeu apos 3 dias",
      chipName: "Julia-01",
      timestamp: new Date(Date.now() - 58 * 60 * 1000).toISOString(),
    },
    {
      id: "event-5",
      type: "alerta",
      message: "trust caiu 8 pontos (56 -> 48)",
      chipName: "Julia-05",
      timestamp: new Date(Date.now() - 75 * 60 * 1000).toISOString(),
    },
    {
      id: "event-6",
      type: "chip",
      message: "graduou do warming (trust: 85)",
      chipName: "Julia-03",
      timestamp: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    },
  ],
  hasMore: true,
};
