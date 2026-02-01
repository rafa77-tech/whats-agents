/**
 * Constantes para o módulo de Integridade
 */

import type { KpiStatus, AnomalySeverity, HealthScoreComponent } from './types'

/**
 * Cores para status de KPI
 */
export const KPI_STATUS_COLORS: Record<
  KpiStatus,
  { border: string; text: string; bg: string; icon: string }
> = {
  good: {
    border: 'border-green-200',
    text: 'text-green-600',
    bg: 'bg-green-100',
    icon: 'text-green-600',
  },
  warn: {
    border: 'border-yellow-200',
    text: 'text-yellow-600',
    bg: 'bg-yellow-100',
    icon: 'text-yellow-600',
  },
  bad: {
    border: 'border-red-200',
    text: 'text-red-600',
    bg: 'bg-red-100',
    icon: 'text-red-600',
  },
}

/**
 * Cores para severidade de anomalia
 */
export const ANOMALY_SEVERITY_COLORS: Record<
  AnomalySeverity,
  { bg: string; text: string; icon: string; badge: string }
> = {
  high: {
    bg: 'bg-red-50',
    text: 'text-red-800',
    icon: 'text-red-500',
    badge: 'bg-red-100 text-red-800',
  },
  medium: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-800',
    icon: 'text-yellow-500',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  low: {
    bg: 'bg-blue-50',
    text: 'text-blue-800',
    icon: 'text-blue-500',
    badge: 'bg-blue-100 text-blue-800',
  },
}

/**
 * Labels para severidade de anomalia
 */
export const ANOMALY_SEVERITY_LABELS: Record<AnomalySeverity, string> = {
  high: 'Alta',
  medium: 'Media',
  low: 'Baixa',
}

/**
 * Ordem de prioridade para severidade (menor = maior prioridade)
 */
export const ANOMALY_SEVERITY_ORDER: Record<AnomalySeverity, number> = {
  high: 0,
  medium: 1,
  low: 2,
}

/**
 * Cores para status de resolução de anomalia
 */
export const ANOMALY_RESOLUTION_COLORS = {
  resolvida: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    icon: 'text-green-500',
  },
  aberta: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    icon: 'text-yellow-500',
  },
}

/**
 * Labels para status de resolução
 */
export const ANOMALY_RESOLUTION_LABELS = {
  resolvida: 'Resolvida',
  aberta: 'Aberta',
}

/**
 * Thresholds para Health Score
 */
export const HEALTH_SCORE_THRESHOLDS = {
  GOOD: 80,
  WARN: 60,
}

/**
 * Thresholds para Taxa de Conversão (%)
 */
export const CONVERSION_RATE_THRESHOLDS = {
  GOOD: 30,
  WARN: 20,
}

/**
 * Thresholds para Time-to-Fill (horas) - menor é melhor
 */
export const TIME_TO_FILL_THRESHOLDS = {
  GOOD: 4,
  WARN: 8,
}

/**
 * Thresholds para cores de progresso (percentual)
 */
export const PROGRESS_THRESHOLDS = {
  GOOD: 80,
  WARN: 60,
}

/**
 * Cores para barras de progresso
 */
export const PROGRESS_COLORS = {
  GOOD: 'bg-green-500',
  WARN: 'bg-yellow-500',
  BAD: 'bg-red-500',
}

/**
 * Componentes do Health Score para exibição
 */
export const HEALTH_SCORE_COMPONENTS: HealthScoreComponent[] = [
  { label: 'Pressao de Vagas', key: 'pressao' },
  { label: 'Friccao no Funil', key: 'friccao' },
  { label: 'Qualidade Respostas', key: 'qualidade' },
  { label: 'Score de Spam', key: 'spam' },
]

/**
 * Valores padrão para KPIs quando não há dados
 */
export const DEFAULT_KPIS = {
  healthScore: 0,
  conversionRate: 0,
  timeToFill: 0,
  componentScores: {
    pressao: 0,
    friccao: 0,
    qualidade: 0,
    spam: 0,
  },
  recommendations: [] as string[],
}

/**
 * Valores padrão para resumo de anomalias
 */
export const DEFAULT_ANOMALIAS_SUMMARY = {
  abertas: 0,
  resolvidas: 0,
  total: 0,
}

/**
 * Limite de anomalias para buscar da API
 */
export const ANOMALIAS_FETCH_LIMIT = 20
