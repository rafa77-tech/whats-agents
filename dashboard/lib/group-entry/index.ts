/**
 * Módulo de Group Entry
 *
 * Exporta tipos, constantes e formatadores para o módulo de entrada em grupos
 */

// Types
export type {
  LinkStatus,
  QueueItemStatus,
  GroupLink,
  QueueItem,
  LinkMetrics,
  QueueMetrics,
  ProcessedTodayMetrics,
  CapacityMetrics,
  GroupEntryDashboard,
  GroupEntryConfig,
  GroupEntryConfigUI,
  LinkFilters,
  ImportResult,
  ImportError,
  LinksResponse,
  QueueResponse,
  DiaSemana,
} from './types'

// Constants
export {
  LINK_STATUS_LABELS,
  LINK_STATUS_BADGE_COLORS,
  QUEUE_STATUS_LABELS,
  QUEUE_STATUS_BADGE_COLORS,
  DIAS_SEMANA,
  DEFAULT_CONFIG,
  CONFIG_LIMITS,
  QUEUE_REFRESH_INTERVAL,
  DEFAULT_LINKS_LIMIT,
  WHATSAPP_LINK_PREFIX,
  ACCEPTED_FILE_EXTENSIONS,
  CAPACITY_WARNING_THRESHOLD,
  CAPACITY_DANGER_THRESHOLD,
} from './constants'

// Formatters
export {
  getLinkStatusLabel,
  getLinkStatusBadgeColor,
  getQueueStatusLabel,
  getQueueStatusBadgeColor,
  formatLinkUrl,
  formatDate,
  formatTime,
  calculateCapacityPercentage,
  getCapacityColor,
  isCapacityWarning,
  configApiToUI,
  configUIToApi,
  validateConfig,
  isValidFileExtension,
} from './formatters'

// Hooks
export {
  useDebounce,
  useGroupEntryDashboard,
  useLinksList,
  useProcessingQueue,
  useGroupEntryConfig,
  useLinkActions,
  useQueueActions,
  useBatchActions,
  useImportLinks,
} from './hooks'
