/**
 * Módulo de Integridade
 *
 * Centraliza tipos, constantes e funções de formatação
 * para o módulo de Integridade dos Dados
 */

// Types
export type {
  KpiStatus,
  AnomalySeverity,
  AnomalyResolutionStatus,
  AnomalyResolutionType,
  Anomaly,
  ComponentScores,
  IntegridadeKpis,
  AnomaliasSummary,
  IntegridadeData,
  HealthScoreComponent,
} from './types'

// Constants
export {
  KPI_STATUS_COLORS,
  ANOMALY_SEVERITY_COLORS,
  ANOMALY_SEVERITY_LABELS,
  ANOMALY_SEVERITY_ORDER,
  ANOMALY_RESOLUTION_COLORS,
  ANOMALY_RESOLUTION_LABELS,
  HEALTH_SCORE_THRESHOLDS,
  CONVERSION_RATE_THRESHOLDS,
  TIME_TO_FILL_THRESHOLDS,
  PROGRESS_THRESHOLDS,
  PROGRESS_COLORS,
  HEALTH_SCORE_COMPONENTS,
  DEFAULT_KPIS,
  DEFAULT_ANOMALIAS_SUMMARY,
  ANOMALIAS_FETCH_LIMIT,
} from './constants'

// Formatters
export {
  getKpiStatusColors,
  getAnomalySeverityColors,
  getAnomalySeverityLabel,
  getAnomalyResolutionColors,
  getAnomalyResolutionLabel,
  getHealthScoreStatus,
  getConversionRateStatus,
  getTimeToFillStatus,
  getProgressColor,
  convertComponentScoreToPercentage,
  sortAnomaliesBySeverity,
  countAnomaliesBySeverity,
  filterOpenAnomalies,
  filterResolvedAnomalies,
  formatDateBR,
  formatDateTimeBR,
  formatResolutionNotes,
  truncateAnomalyId,
} from './formatters'

// Hooks
export { useIntegridadeData, parseKpisResponse, parseAnomaliasResponse } from './hooks'
