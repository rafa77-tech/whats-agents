/**
 * Módulo Health Center - Exports centralizados
 */

// Types
export type {
  HealthStatus,
  ServiceStatusType,
  AlertSeverity,
  CircuitState,
  HealthAlert,
  Circuit,
  Service,
  RateLimitData,
  QueueData,
  HealthData,
  RefreshIntervalOption,
} from './types'

// Re-export from centralized types
export type {
  HealthScoreResponse,
  HealthAlertResponse,
  CircuitBreakerStatus,
  CircuitHistoryEntry,
  RateLimitStats,
  QueueStats,
  ServiceStatus,
  HealthOverviewResponse,
} from './types'

// Constants
export {
  HEALTH_STATUS_COLORS,
  HEALTH_STATUS_LABELS,
  SERVICE_STATUS_COLORS,
  ALERT_SEVERITY_COLORS,
  ALERT_SEVERITY_LABELS,
  ALERT_SEVERITY_ORDER,
  CIRCUIT_STATE_COLORS,
  CIRCUIT_STATE_LEGEND,
  REFRESH_INTERVALS,
  DEFAULT_REFRESH_INTERVAL,
  DEFAULT_RATE_LIMIT,
  PROGRESS_THRESHOLDS,
  PROGRESS_COLORS,
  GAUGE_CONFIG,
  MAX_DISPLAYED_ALERTS,
  DEFAULT_SERVICES,
  DEFAULT_CIRCUITS,
} from './constants'

// Formatters
export {
  formatTempoMedio,
  getProgressColor,
  shouldShowRateLimitWarning,
  calculatePercentage,
  getHealthStatusColors,
  getHealthStatusLabel,
  getServiceStatusColors,
  getAlertSeverityColors,
  getAlertSeverityLabel,
  getCircuitStateColors,
  sortAlertsBySeverity,
  countAlertsBySeverity,
  calculateGaugeOffset,
  formatPlural,
  getHealthStatusFromScore,
  getServiceStatusFromScore,
} from './formatters'
