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
    border: 'border-status-success-border',
    text: 'text-status-success-foreground',
    bg: 'bg-status-success',
    icon: 'text-status-success-foreground',
  },
  warn: {
    border: 'border-status-warning-border',
    text: 'text-status-warning-foreground',
    bg: 'bg-status-warning',
    icon: 'text-status-warning-foreground',
  },
  bad: {
    border: 'border-status-error-border',
    text: 'text-status-error-foreground',
    bg: 'bg-status-error',
    icon: 'text-status-error-foreground',
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
    bg: 'bg-status-error/20',
    text: 'text-status-error-foreground',
    icon: 'text-status-error-foreground',
    badge: 'bg-status-error text-status-error-foreground',
  },
  medium: {
    bg: 'bg-status-warning/20',
    text: 'text-status-warning-foreground',
    icon: 'text-status-warning-foreground',
    badge: 'bg-status-warning text-status-warning-foreground',
  },
  low: {
    bg: 'bg-status-info/20',
    text: 'text-status-info-foreground',
    icon: 'text-status-info-foreground',
    badge: 'bg-status-info text-status-info-foreground',
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
    bg: 'bg-status-success',
    text: 'text-status-success-foreground',
    icon: 'text-status-success-foreground',
  },
  aberta: {
    bg: 'bg-status-warning',
    text: 'text-status-warning-foreground',
    icon: 'text-status-warning-foreground',
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
  GOOD: 'bg-status-success-solid',
  WARN: 'bg-status-warning-solid',
  BAD: 'bg-status-error-solid',
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
